"""
VSync Engine — Spectrum LiDAR Render Trigger
Fires a virtual-sync signal from the machine graphics process when the spectrum
lidar pipeline builds mesh topology (geometry of the scanned space).

Architecture:
  LiDAR scan -> Spectrum frequency map -> Mesh topology builder
     -> VSync trigger (machine process) -> Render frame committed
     -> Vysync actual ↔ map alignment confirmed

VSync here mirrors GPU vertical-sync logic: we hold the render commit until
the geometry frame is fully assembled, then fire once — preventing partial or
torn mesh renders being fed downstream to the navigation stack.
"""

import time
import math
import threading
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger("light-asi.vsync")


# ── VSync states (mirrors GPU display pipeline) ──────────────────────────────

class VSyncState(Enum):
    IDLE           = "idle"            # waiting for scan data
    ACCUMULATING   = "accumulating"    # collecting lidar points into frame
    GEOMETRY_READY = "geometry_ready"  # mesh topology computed, pending sync
    SYNCED         = "synced"          # render trigger fired, frame committed
    DROPPED        = "dropped"         # frame missed timing window — retry


class MeshBuildState(Enum):
    EMPTY     = "empty"
    PARTIAL   = "partial"
    COMPLETE  = "complete"
    VALIDATED = "validated"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SpectrumLidarFrame:
    """One render frame's worth of spectrum lidar data."""
    frame_id:        int
    scan_points:     List[Dict[str, float]]   # raw lidar hits
    spectrum_map:    Dict[float, List[Tuple[float, float]]]  # freq -> [(x,y)]
    mesh_vertices:   np.ndarray               # Nx3 float32
    mesh_faces:      np.ndarray               # Mx3 int32
    density_grid:    np.ndarray               # 2-D occupancy
    timestamp_start: float
    timestamp_end:   float = 0.0
    vsync_fired:     bool  = False
    build_state:     MeshBuildState = MeshBuildState.EMPTY

    @property
    def frame_duration_ms(self) -> float:
        if self.timestamp_end:
            return (self.timestamp_end - self.timestamp_start) * 1000.0
        return 0.0


@dataclass
class VSyncEvent:
    """Emitted once per completed render frame."""
    frame_id:       int
    fired_at:       float
    mesh_vertices:  int
    mesh_faces:     int
    spectrum_bands: int
    density_coverage: float   # fraction of grid cells populated
    render_latency_ms: float
    aligned:        bool      # vysync actual ↔ map agreement


# ── VSync Engine ─────────────────────────────────────────────────────────────

class VSyncEngine:
    """
    Machine-process render trigger for spectrum LiDAR mesh topology.

    Usage:
        engine = VSyncEngine(grid_bounds=(-50,50,-50,50), resolution=0.5)
        engine.on_vsync(my_render_callback)
        engine.ingest_scan(lidar_points, spectrum_freqs)   # called each scan cycle
    """

    # Target 20 Hz render cycle (50 ms) — matches Tesla sensor fusion rate
    TARGET_FRAME_MS: float = 50.0
    # Minimum mesh vertex count before we allow a vsync trigger
    MIN_VERTICES:    int   = 4
    # Maximum ms we wait before forcing a vsync with whatever we have
    MAX_WAIT_MS:     float = 100.0

    def __init__(
        self,
        grid_bounds: Tuple[float, float, float, float] = (-50.0, 50.0, -50.0, 50.0),
        resolution:  float = 0.5,
    ):
        self.grid_bounds = grid_bounds
        self.resolution  = resolution

        x_min, x_max, y_min, y_max = grid_bounds
        self._grid_w = max(1, int((x_max - x_min) / resolution))
        self._grid_h = max(1, int((y_max - y_min) / resolution))

        # Frame management
        self._frame_counter   = 0
        self._current_frame:  Optional[SpectrumLidarFrame] = None
        self._frame_history:  List[VSyncEvent] = []
        self._lock            = threading.Lock()

        # VSync state machine
        self.state            = VSyncState.IDLE
        self._frame_open_at:  float = 0.0

        # Callbacks fired on vsync
        self._vsync_callbacks: List[Callable[[VSyncEvent, SpectrumLidarFrame], None]] = []

        # Vysync alignment: actual sonar data vs stored map
        self._vysync_actual:  List[Dict] = []
        self._vysync_map:     List[Dict] = []
        self._last_alignment: float = 0.0
        self._alignment_score: float = 0.0

        # Stats
        self.stats = {
            "frames_synced":  0,
            "frames_dropped": 0,
            "avg_latency_ms": 0.0,
            "last_vsync_at":  0.0,
        }

        logger.info(
            f"VSyncEngine ready  grid={self._grid_w}x{self._grid_h}  "
            f"res={resolution}m  target={self.TARGET_FRAME_MS}ms"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def on_vsync(self, callback: Callable[[VSyncEvent, SpectrumLidarFrame], None]):
        """Register a callback fired on every committed render frame."""
        self._vsync_callbacks.append(callback)

    def ingest_scan(
        self,
        lidar_points:    List[Dict[str, float]],
        spectrum_freqs:  List[Dict[str, Any]],
        vysync_actual:   Optional[List[Dict]] = None,
        vysync_map:      Optional[List[Dict]] = None,
    ) -> Optional[VSyncEvent]:
        """
        Feed one LiDAR scan cycle into the engine.
        Returns a VSyncEvent if this scan completed a frame, else None.

        lidar_points  – list of {x, y, z, intensity, distance}
        spectrum_freqs – list of {frequency, coord_x, coord_y, confidence, …}
        vysync_actual  – sonar actual-path data (for alignment check)
        vysync_map     – stored map data (for alignment check)
        """
        with self._lock:
            now = time.perf_counter()

            # Update vysync reference data if provided
            if vysync_actual is not None:
                self._vysync_actual = vysync_actual
            if vysync_map is not None:
                self._vysync_map = vysync_map

            # Open a new frame if we are idle
            if self.state == VSyncState.IDLE:
                self._open_frame(now)

            # Accumulate data into current frame
            self.state = VSyncState.ACCUMULATING
            self._accumulate(lidar_points, spectrum_freqs)

            # Build mesh topology from accumulated data
            build_ok = self._build_mesh_topology()

            # Decide whether to fire vsync
            frame_age_ms = (now - self._frame_open_at) * 1000.0
            ready = (
                build_ok
                and self._current_frame.build_state == MeshBuildState.COMPLETE
                and len(self._current_frame.scan_points) >= self.MIN_VERTICES
            )
            forced = frame_age_ms >= self.MAX_WAIT_MS

            if ready or forced:
                event = self._fire_vsync(now, forced=forced)
                return event

            return None

    def feed_vysync_data(self, actual: List[Dict], map_data: List[Dict]):
        """
        Provide the actual sonar paths and map template for alignment.
        Called by the ASI integration layer (replaces the old vysync_coordinate_data).
        """
        with self._lock:
            self._vysync_actual = actual
            self._vysync_map    = map_data
            self._last_alignment = time.time()
            self._alignment_score = self._compute_alignment_score()
        logger.debug(f"VSync alignment updated: score={self._alignment_score:.3f}")

    def get_latest_frame(self) -> Optional[SpectrumLidarFrame]:
        """Return the most-recently committed frame (thread-safe copy)."""
        with self._lock:
            return self._current_frame

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "state":            self.state.value,
            "alignment_score":  round(self._alignment_score, 4),
            "frame_history_len": len(self._frame_history),
            "grid_dims":        (self._grid_w, self._grid_h),
            "resolution_m":     self.resolution,
        }

    # ── Frame lifecycle ───────────────────────────────────────────────────────

    def _open_frame(self, now: float):
        self._frame_counter += 1
        x_min, _, y_min, _ = self.grid_bounds

        self._current_frame = SpectrumLidarFrame(
            frame_id        = self._frame_counter,
            scan_points     = [],
            spectrum_map    = {},
            mesh_vertices   = np.empty((0, 3), dtype=np.float32),
            mesh_faces      = np.empty((0, 3), dtype=np.int32),
            density_grid    = np.zeros((self._grid_h, self._grid_w), dtype=np.float32),
            timestamp_start = now,
        )
        self._frame_open_at = now
        self.state = VSyncState.IDLE
        logger.debug(f"Frame {self._frame_counter} opened")

    def _accumulate(
        self,
        lidar_points:   List[Dict[str, float]],
        spectrum_freqs: List[Dict[str, Any]],
    ):
        """Merge new scan data into the open frame."""
        f = self._current_frame
        x_min, x_max, y_min, y_max = self.grid_bounds

        # --- LiDAR points -> density grid ---
        for pt in lidar_points:
            x, y = pt.get("x", 0.0), pt.get("y", 0.0)
            xi = int((x - x_min) / self.resolution)
            yi = int((y - y_min) / self.resolution)
            if 0 <= xi < self._grid_w and 0 <= yi < self._grid_h:
                intensity = pt.get("intensity", 1.0)
                f.density_grid[yi, xi] = min(1.0, f.density_grid[yi, xi] + intensity * 0.1)
                f.scan_points.append(pt)

        # --- Spectrum frequencies -> frequency band map ---
        for sf in spectrum_freqs:
            freq  = sf.get("frequency", 0.0)
            cx, cy = sf.get("coord_x", 0.0), sf.get("coord_y", 0.0)
            bucket = round(freq / 10.0) * 10.0
            f.spectrum_map.setdefault(bucket, []).append((cx, cy))

        f.build_state = MeshBuildState.PARTIAL

    def _build_mesh_topology(self) -> bool:
        """
        Convert the density grid into a triangulated mesh topology.
        This is the geometry-of-space step that gates the vsync trigger.
        """
        f = self._current_frame
        if f is None or f.build_state == MeshBuildState.EMPTY:
            return False

        try:
            vertices, faces = self._marching_squares_mesh(f.density_grid)

            if len(vertices) < self.MIN_VERTICES:
                # Not enough geometry yet — stay partial
                return False

            f.mesh_vertices = vertices
            f.mesh_faces    = faces
            f.build_state   = MeshBuildState.COMPLETE
            return True

        except Exception as e:
            logger.warning(f"Mesh build failed frame {f.frame_id}: {e}")
            return False

    def _marching_squares_mesh(
        self, density: np.ndarray, threshold: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Lightweight marching-squares triangulation of the 2-D density grid.
        Returns (vertices Nx3 float32, faces Mx3 int32).
        """
        x_min, _, y_min, _ = self.grid_bounds
        h, w = density.shape
        verts: List[List[float]] = []
        faces: List[List[int]]   = []

        def _vi(x, y, z=0.0):
            idx = len(verts)
            verts.append([x, y, z])
            return idx

        for row in range(h - 1):
            for col in range(w - 1):
                # Sample 2x2 cell
                d00 = density[row,   col]
                d10 = density[row,   col+1]
                d01 = density[row+1, col]
                d11 = density[row+1, col+1]

                above = [v > threshold for v in (d00, d10, d01, d11)]
                case  = sum(b << i for i, b in enumerate(above))

                if case in (0, 15):
                    continue  # fully outside or inside — no edge

                # World-space corners
                wx = x_min + col * self.resolution
                wy = y_min + row * self.resolution
                wx1, wy1 = wx + self.resolution, wy + self.resolution

                # Midpoints on cell edges (simple linear interpolation)
                mx_t = wx  + self.resolution * 0.5  # top edge
                mx_b = wx  + self.resolution * 0.5  # bottom
                my_l = wy  + self.resolution * 0.5  # left
                my_r = wy  + self.resolution * 0.5  # right

                # Average density as Z (height field for 3-D mesh)
                avg_z = float(np.mean([d00, d10, d01, d11]))

                v0 = _vi(wx,   wy,  avg_z)
                v1 = _vi(wx1,  wy,  avg_z)
                v2 = _vi(wx,   wy1, avg_z)
                v3 = _vi(wx1,  wy1, avg_z)

                # Two triangles per occupied cell
                if above[0] or above[1] or above[2]:
                    faces.append([v0, v1, v2])
                if above[1] or above[2] or above[3]:
                    faces.append([v1, v3, v2])

        if not verts:
            return np.empty((0, 3), np.float32), np.empty((0, 3), np.int32)

        return (
            np.array(verts, dtype=np.float32),
            np.array(faces, dtype=np.int32) if faces else np.empty((0, 3), np.int32),
        )

    # ── VSync trigger ─────────────────────────────────────────────────────────

    def _fire_vsync(self, now: float, forced: bool = False) -> VSyncEvent:
        """Commit the current frame and fire all registered callbacks."""
        f = self._current_frame
        f.timestamp_end = now
        f.vsync_fired   = True

        # Alignment with vysync actual/map data
        aligned = self._alignment_score >= 0.70

        coverage = float(np.count_nonzero(f.density_grid)) / max(1, f.density_grid.size)

        event = VSyncEvent(
            frame_id          = f.frame_id,
            fired_at          = now,
            mesh_vertices     = len(f.mesh_vertices),
            mesh_faces        = len(f.mesh_faces),
            spectrum_bands    = len(f.spectrum_map),
            density_coverage  = coverage,
            render_latency_ms = f.frame_duration_ms,
            aligned           = aligned,
        )

        self._frame_history.append(event)

        # Update stats
        self.stats["frames_synced"] += 1
        self.stats["last_vsync_at"]  = now
        latencies = [e.render_latency_ms for e in self._frame_history[-20:]]
        self.stats["avg_latency_ms"] = sum(latencies) / len(latencies)

        label = "FORCED" if forced else "READY"
        logger.info(
            f"[VSYNC {label}] frame={f.frame_id}  "
            f"verts={event.mesh_vertices}  faces={event.mesh_faces}  "
            f"bands={event.spectrum_bands}  cov={coverage:.1%}  "
            f"latency={f.frame_duration_ms:.1f}ms  aligned={aligned}"
        )

        # Fire callbacks (non-blocking)
        for cb in self._vsync_callbacks:
            try:
                cb(event, f)
            except Exception as e:
                logger.error(f"VSync callback error: {e}")

        # Transition: mark state synced, next ingest opens a fresh frame
        self.state = VSyncState.SYNCED
        # Immediately reopen so the next ingest doesn't have to wait
        self._open_frame(now)

        return event

    # ── Alignment (vysync actual ↔ map) ──────────────────────────────────────

    def _compute_alignment_score(self) -> float:
        """Score how well actual sonar paths align with stored map data."""
        if not self._vysync_actual or not self._vysync_map:
            return 0.0

        scores = []
        for actual_pt in self._vysync_actual[:50]:   # cap for speed
            ax, ay = actual_pt.get("x", 0.0), actual_pt.get("y", 0.0)
            best = min(
                (math.sqrt((mp.get("x", 0) - ax)**2 + (mp.get("y", 0) - ay)**2)
                 for mp in self._vysync_map),
                default=999.0,
            )
            # Score: 1.0 if distance=0, 0.0 if distance ≥ 10 m
            scores.append(max(0.0, 1.0 - best / 10.0))

        return sum(scores) / len(scores) if scores else 0.0