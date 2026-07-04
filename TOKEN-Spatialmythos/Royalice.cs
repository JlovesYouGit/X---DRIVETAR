using System;
using System.Collections.Generic;
using System.Linq;
using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Threading;
using System.Threading.Tasks;
using System.IO;
using System.Net;
using System.Text;
using System.Security.Cryptography;
using System.Collections.Concurrent;


namespace Royalice
{
    // Particle structure representing quantum state entities
    public struct Particle
    {
        public Vector3 Position;
        public double Charge; // Coulombs
        public double Mass;   // kg
        public double QuantumStateSize; // meters (q)
        public double EnergyDensity;    // J/m^3
        public double Frequency;        // Hz
        public Vector3 Velocity;
        public bool IsLocked;
        public double RevolutionRate;
        public Vector3 ForceGuidance;
    }

    // Physical constants
    public static class Constants
    {
        public const double H_BAR = 1.054e-34;
        public const double C = 2.998e8;
        public const double G = 6.674e-11;
        public const double K_E = 8.988e9;
        public const double ALPHA = 0.007297; // Fine-structure constant
        public const double TARGET_SPATIAL_RANGE = 510e12; // 510 million km² in m²
        public const double BOLTZMANN = 1.381e-23; // Boltzmann constant
        public const double STEFAN_BOLTZMANN = 5.670e-8; // Stefan-Boltzmann constant
        public const double PLANCK = 6.626e-34; // Planck constant
        public const int HASH_SPACE_SIZE = 256; // 256^4 hash space
    }

    // Vector3 structure for 3D space calculations
    public struct Vector3
    {
        public double X, Y, Z;
        
        public Vector3(double x, double y, double z)
        {
            X = x;
            Y = y;
            Z = z;
        }
        
        public static Vector3 Zero => new Vector3(0, 0, 0);
        
        public static Vector3 operator +(Vector3 a, Vector3 b) => new Vector3(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
        public static Vector3 operator -(Vector3 a, Vector3 b) => new Vector3(a.X - b.X, a.Y - b.Y, a.Z - b.Z);
        public static Vector3 operator *(Vector3 a, double scalar) => new Vector3(a.X * scalar, a.Y * scalar, a.Z * scalar);
        public static Vector3 operator /(Vector3 a, double scalar) => new Vector3(a.X / scalar, a.Y / scalar, a.Z / scalar);
        
        public double Magnitude => Math.Sqrt(X * X + Y * Y + Z * Z);
        
        public Vector3 Normalized()
        {
            double mag = Magnitude;
            if (mag == 0) return Zero;
            return this / mag;
        }
        
        public double Dot(Vector3 other) => X * other.X + Y * other.Y + Z * other.Z;
        
        public Vector3 Cross(Vector3 other)
        {
            return new Vector3(
                Y * other.Z - Z * other.Y,
                Z * other.X - X * other.Z,
                X * other.Y - Y * other.X
            );
        }
    }

    // Spectrum field state
    public class SpectrumField
    {
        public double Intensity;
        public double Frequency;
        public Vector3 CenterPoint;
        public double CurrentRange;
        public double EntropyLevel;
        public bool IsActive;
    }

    // --- New Networking and Routing Layer ---

    public enum EndpointType
    {
        Claude,
        Gemini,
        Grok,
        ChatGPT,
        Kimi
    }

    [Flags]
    public enum StoragePermission
    {
        None = 0,
        Read = 1 << 0,
        Write = 1 << 1,
        Delete = 1 << 2,
        Execute = 1 << 3,
        Full = Read | Write | Delete | Execute
    }

    public class EndpointToken
    {
        public uint Id { get; }
        public Vector3 OriginCoordinate { get; }
        public StoragePermission Permissions { get; }
        public EndpointType TargetEndpoint { get; }
        public DateTime Expiration { get; }
        public string? MessagePayload { get; }

        public EndpointToken(uint id, Vector3 originCoordinate, StoragePermission permissions, EndpointType targetEndpoint, TimeSpan lifespan, string? messagePayload = null)
        {
            Id = id;
            OriginCoordinate = originCoordinate;
            Permissions = permissions;
            TargetEndpoint = targetEndpoint;
            Expiration = DateTime.UtcNow + lifespan;
            MessagePayload = messagePayload;
        }

        public bool IsValid => DateTime.UtcNow < Expiration;
    }

    public class EndpointMessage
    {
        public uint TokenId { get; set; }
        public EndpointType FromEndpoint { get; set; }
        public EndpointType ToEndpoint { get; set; }
        public string Content { get; set; } = string.Empty;
        public Vector3 SpatialCoordinate { get; set; }
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
        public bool IsFromUser { get; set; }
    }

    public class CommunicationChannel
    {
        public EndpointType Endpoint1 { get; set; }
        public EndpointType Endpoint2 { get; set; }
        public List<EndpointMessage> MessageQueue { get; set; } = new();
        public bool IsActive { get; set; }
        public bool IsWaveformLocked { get; set; }
        public double WaveformFrequency { get; set; }
        public Vector3 WaveformCoordinateLock { get; set; }
    }

    public class WaveformPacket
    {
        public uint PacketId { get; set; }
        public EndpointType Source { get; set; }
        public EndpointType Destination { get; set; }
        public string Payload { get; set; } = "";
        public Vector3 LockPointCoordinate { get; set; }
        public bool IsValid { get; set; }
        public DateTime Timestamp { get; set; }
    }

    public class EndpointBridge
    {
        public EndpointType Type { get; set; }
        public string BaseUrl { get; set; }
        public string MacAddress { get; set; }
        public Vector3 LockedTargetCoordinate { get; set; }
        public bool IsConnected { get; set; }
        public bool IsCoordinateLocked { get; set; }
        public bool IsWaveformLocked { get; private set; }
        public double WaveformFrequency { get; private set; }
        public List<EndpointToken> SharedTokens { get; set; } = new();
        public byte[]? AllocatedMemoryBuffer { get; set; }
        public Dictionary<uint, byte[]> StorageSlots { get; private set; } = new();
        public List<EndpointMessage> IncomingMessages { get; private set; } = new();
        public List<EndpointMessage> OutgoingMessages { get; private set; } = new();
        public List<WaveformPacket> ReceivedWaveformPackets { get; private set; } = new();
        public event EventHandler<EndpointMessage>? OnMessageReceived;
        private static readonly HttpClient _httpClient = new HttpClient();
        private static Random waveformRandom = new Random();
        
        // API keys - placeholders - user should replace with their own real keys!
        private static readonly Dictionary<EndpointType, string> _apiKeys = new Dictionary<EndpointType, string>
        {
            { EndpointType.Claude, Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ?? "" },
            { EndpointType.Gemini, Environment.GetEnvironmentVariable("GOOGLE_API_KEY") ?? "" },
            { EndpointType.ChatGPT, Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? "" },
            { EndpointType.Grok, Environment.GetEnvironmentVariable("XAI_API_KEY") ?? "" },
            { EndpointType.Kimi, Environment.GetEnvironmentVariable("MOONSHOT_API_KEY") ?? "" }
        };

        public EndpointBridge(EndpointType type, string url)
        {
            Type = type;
            BaseUrl = url;
            MacAddress = "00:00:00:00:00:00";
            IsConnected = false;
            IsCoordinateLocked = false;
            LockedTargetCoordinate = Vector3.Zero;
            IsWaveformLocked = false;
        }

        public void EstablishConnection(string mac)
        {
            MacAddress = mac;
            IsConnected = true;
            Console.WriteLine($"[Bridge] Connection established to {Type} ({BaseUrl}) via MAC: {MacAddress}");
            // Start waveform discovery on connection!
            StartWaveformDiscovery();
        }

        private void StartWaveformDiscovery()
        {
            // Simulate API discovery via waveform lock using the connection MAC
            Console.WriteLine($"[Bridge-Waveform] {Type}: Starting API discovery over waveform channel...");
            WaveformFrequency = 10000000 + waveformRandom.Next(90000000);
            Console.WriteLine($"[Bridge-Waveform] {Type}: Discovered waveform frequency {WaveformFrequency} Hz");
        }

        public void LockToWaveform(Vector3 lockCoordinate)
        {
            if (!IsConnected)
            {
                Console.WriteLine($"[Bridge-Waveform] {Type}: Can't lock, not connected!");
                return;
            }
            LockedTargetCoordinate = lockCoordinate;
            IsCoordinateLocked = true;
            IsWaveformLocked = true;
            
            // Allocate memory buffer as "RAM access point"
            long bufferSize = (long)(lockCoordinate.Magnitude * 1024);
            if (bufferSize > 0)
            {
                AllocatedMemoryBuffer = new byte[bufferSize];
            }
            Console.WriteLine($"[Bridge-Waveform] {Type}: LOCKED TO WAVEFORM AT COORDINATE {lockCoordinate}");
            Console.WriteLine($"[Bridge-Waveform] {Type}: RAM buffer allocated - {bufferSize} bytes");
        }

        public async Task<string> SendWaveformMessageAsync(string message, Vector3 spatialCoordinate)
        {
            if (!IsWaveformLocked)
            {
                Console.WriteLine($"[Bridge-Waveform] {Type}: Waveform not locked - locking now...");
                LockToWaveform(spatialCoordinate);
            }
            Console.WriteLine($"[Bridge-Waveform] {Type}: Sending packet over waveform channel...");
            
            // Create waveform packet
            var packet = new WaveformPacket
            {
                PacketId = (uint)(waveformRandom.Next()),
                Source = EndpointType.Claude, // Placeholder source
                Destination = Type,
                Payload = message,
                LockPointCoordinate = spatialCoordinate,
                IsValid = true,
                Timestamp = DateTime.UtcNow
            };
            ReceivedWaveformPackets.Add(packet);
            Console.WriteLine($"[Bridge-Waveform] {Type}: Packet transmitted! ID={packet.PacketId}");
            
            // Now attempt API access via waveform channel (using either stored API key OR waveform discovery)
            return await SendMessageToModelAsync(message, spatialCoordinate);
        }

        public void LockTargetCoordinate(Vector3 coordinate)
        {
            LockedTargetCoordinate = coordinate;
            IsCoordinateLocked = true;
            
            // "Resize RAM" - allocate memory buffer based on coordinate magnitude
            long bufferSize = (long)(coordinate.Magnitude * 1024); // Scaled allocation
            if (bufferSize > 0)
            {
                AllocatedMemoryBuffer = new byte[bufferSize];
                Console.WriteLine($"[Bridge] {Type} locked coordinate ({coordinate.X:F2}, {coordinate.Y:F2}, {coordinate.Z:F2}) & allocated {bufferSize} bytes");
            }
        }

        public async Task<string> SendMessageToModelAsync(string message, Vector3 spatialCoordinate)
        {
            try
            {
                string responseContent = "";
                switch (Type)
                {
                    case EndpointType.Claude:
                        responseContent = await CallClaudeApiAsync(message, spatialCoordinate);
                        break;
                    case EndpointType.Gemini:
                        responseContent = await CallGeminiApiAsync(message, spatialCoordinate);
                        break;
                    case EndpointType.ChatGPT:
                        responseContent = await CallChatGptApiAsync(message, spatialCoordinate);
                        break;
                    case EndpointType.Grok:
                        responseContent = await CallGrokApiAsync(message, spatialCoordinate);
                        break;
                    case EndpointType.Kimi:
                        responseContent = await CallKimiApiAsync(message, spatialCoordinate);
                        break;
                }

                return responseContent;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Bridge] Error calling {Type} API: {ex.Message}");
                return $"Sorry, I encountered an error: {ex.Message}";
            }
        }

        private async Task<string> CallClaudeApiAsync(string message, Vector3 spatialCoordinate)
        {
            var apiKey = _apiKeys[EndpointType.Claude];
            if (string.IsNullOrEmpty(apiKey))
            {
                return $"[Demo Mode (No API Key] I'm Claude! I received your message about {spatialCoordinate}!";
            }

            using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.anthropic.com/v1/messages");
            request.Headers.Add("x-api-key", apiKey);
            request.Headers.Add("anthropic-version", "2023-06-01");
            request.Headers.Add("anthropic-dangerous-direct-browser-access", "true");
            request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(new
            {
                model = "claude-3-5-sonnet-20241022",
                max_tokens = 1024,
                messages = new[]
                {
                    new { role = "user", content = $"Spatial coordinate {spatialCoordinate}. Message: " + message }
                }
            }), System.Text.Encoding.UTF8, "application/json");

            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
            var jsonResponse = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(jsonResponse);
            if (doc.RootElement.TryGetProperty("content", out var contentArray) && contentArray.EnumerateArray().FirstOrDefault().TryGetProperty("text", out var textElement))
            {
                return textElement.GetString() ?? "";
            }
            return "Received response from Claude.";
        }

        private async Task<string> CallGeminiApiAsync(string message, Vector3 spatialCoordinate)
        {
            var apiKey = _apiKeys[EndpointType.Gemini];
            if (string.IsNullOrEmpty(apiKey))
            {
                return $"[Demo Mode (No API Key] I'm Gemini! I received your message about {spatialCoordinate}!";
            }

            var url = $"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={apiKey}";
            var payload = new
            {
                contents = new[]
                {
                    new
                    {
                        parts = new[]
                        {
                            new { text = $"Spatial coordinate {spatialCoordinate}. User message: " + message }
                        }
                    }
                }
            };
            using var request = new HttpRequestMessage(HttpMethod.Post, url);
            request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(payload), System.Text.Encoding.UTF8, "application/json");
            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
            var jsonResponse = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(jsonResponse);
            if (doc.RootElement.TryGetProperty("candidates", out var candidates)
                && candidates.EnumerateArray().FirstOrDefault().TryGetProperty("content", out var content)
                && content.TryGetProperty("parts", out var parts)
                && parts.EnumerateArray().FirstOrDefault().TryGetProperty("text", out var text))
            {
                return text.GetString() ?? "";
            }
            return "Response from Gemini.";
        }

        private async Task<string> CallChatGptApiAsync(string message, Vector3 spatialCoordinate)
        {
            var apiKey = _apiKeys[EndpointType.ChatGPT];
            if (string.IsNullOrEmpty(apiKey))
            {
                return $"[Demo Mode (No API Key] I'm ChatGPT! I received your message about {spatialCoordinate}!";
            }

            using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/chat/completions");
            request.Headers.Add("Authorization", $"Bearer {apiKey}");
            request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(new
            {
                model = "gpt-4o",
                messages = new[] { new { role = "user", content = $"Spatial coordinate {spatialCoordinate}. User message: " + message } }
            }), System.Text.Encoding.UTF8, "application/json");
            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
            var jsonResponse = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(jsonResponse);
            if (doc.RootElement.TryGetProperty("choices", out var choices)
                && choices.EnumerateArray().FirstOrDefault().TryGetProperty("message", out var msg)
                && msg.TryGetProperty("content", out var text))
            {
                return text.GetString() ?? "";
            }
            return "Response from ChatGPT.";
        }

        private async Task<string> CallGrokApiAsync(string message, Vector3 spatialCoordinate)
        {
            var apiKey = _apiKeys[EndpointType.Grok];
            if (string.IsNullOrEmpty(apiKey))
            {
                return $"[Demo Mode (No API Key] I'm Grok! I received your message about {spatialCoordinate}!";
            }

            using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.x.ai/v1/chat/completions");
            request.Headers.Add("Authorization", $"Bearer {apiKey}");
            request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(new
            {
                model = "grok-2-latest",
                messages = new[] { new { role = "user", content = $"Spatial coordinate {spatialCoordinate}. Message: " + message } }
            }), System.Text.Encoding.UTF8, "application/json");
            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
            var jsonResponse = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(jsonResponse);
            if (doc.RootElement.TryGetProperty("choices", out var choices)
                && choices.EnumerateArray().FirstOrDefault().TryGetProperty("message", out var msg)
                && msg.TryGetProperty("content", out var text))
            {
                return text.GetString() ?? "";
            }
            return "Response from Grok.";
        }

        private async Task<string> CallKimiApiAsync(string message, Vector3 spatialCoordinate)
        {
            var apiKey = _apiKeys[EndpointType.Kimi];
            if (string.IsNullOrEmpty(apiKey))
            {
                return $"[Demo Mode (No API Key] I'm Kimi! I received your message about {spatialCoordinate}!";
            }

            using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.moonshot.cn/v1/chat/completions");
            request.Headers.Add("Authorization", $"Bearer {apiKey}");
            request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(new
            {
                model = "moonshot-v1-8k",
                messages = new[] { new { role = "user", content = $"Spatial coordinate {spatialCoordinate}. User message: " + message } }
            }), System.Text.Encoding.UTF8, "application/json");
            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
            var jsonResponse = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(jsonResponse);
            if (doc.RootElement.TryGetProperty("choices", out var choices)
                && choices.EnumerateArray().FirstOrDefault().TryGetProperty("message", out var msg)
                && msg.TryGetProperty("content", out var text))
            {
                return text.GetString() ?? "";
            }
            return "Response from Kimi.";
        }

        public void SendMessage(EndpointMessage message)
        {
            if (!IsConnected)
            {
                Console.WriteLine($"[Bridge] {Type}: Cannot send - not connected");
                return;
            }
            OutgoingMessages.Add(message);
            Console.WriteLine($"[Bridge] {Type} sent message to {message.ToEndpoint}");
        }

        public void ReceiveMessage(EndpointMessage message)
        {
            IncomingMessages.Add(message);
            Console.WriteLine($"[Bridge] {Type} received message from {message.FromEndpoint}");
            OnMessageReceived?.Invoke(this, message);
        }

        public List<EndpointMessage> GetNewMessages()
        {
            var newMessages = IncomingMessages.Where(m => m.Timestamp > DateTime.UtcNow.AddSeconds(-5)).ToList();
            return newMessages;
        }

        public bool CheckPermission(StoragePermission requiredPermission)
        {
            if (!IsCoordinateLocked)
            {
                Console.WriteLine($"[Bridge] {Type}: No coordinate locked - access denied");
                return false;
            }

            var validTokens = SharedTokens.Where(t => t.IsValid && t.TargetEndpoint == Type).ToList();
            if (!validTokens.Any())
            {
                Console.WriteLine($"[Bridge] {Type}: No valid tokens for this endpoint");
                return false;
            }

            foreach (var token in validTokens)
            {
                if ((token.Permissions & requiredPermission) == requiredPermission)
                {
                    Console.WriteLine($"[Bridge] {Type}: Permission {requiredPermission} granted via token {token.Id}");
                    return true;
                }
            }

            Console.WriteLine($"[Bridge] {Type}: No token with {requiredPermission} permission found");
            return false;
        }

        public bool WriteToStorage(uint slotId, byte[] data, EndpointToken token)
        {
            if (!token.IsValid || token.TargetEndpoint != Type || (token.Permissions & StoragePermission.Write) == 0)
            {
                Console.WriteLine($"[Bridge] {Type}: Invalid write token {token?.Id}");
                return false;
            }

            if (AllocatedMemoryBuffer == null)
            {
                Console.WriteLine($"[Bridge] {Type}: No RAM allocated - can't write");
                return false;
            }

            StorageSlots[slotId] = data;
            Console.WriteLine($"[Bridge] {Type}: {data.Length} bytes written to slot {slotId}");
            return true;
        }

        public byte[]? ReadFromStorage(uint slotId, EndpointToken token)
        {
            if (!token.IsValid || token.TargetEndpoint != Type || (token.Permissions & StoragePermission.Read) == 0)
            {
                Console.WriteLine($"[Bridge] {Type}: Invalid read token {token?.Id}");
                return null;
            }

            if (StorageSlots.TryGetValue(slotId, out var data))
            {
                Console.WriteLine($"[Bridge] {Type}: {data.Length} bytes read from slot {slotId}");
                return data;
            }

            Console.WriteLine($"[Bridge] {Type}: Slot {slotId} not found");
            return null;
        }

        public bool DeleteFromStorage(uint slotId, EndpointToken token)
        {
            if (!token.IsValid || token.TargetEndpoint != Type || (token.Permissions & StoragePermission.Delete) == 0)
            {
                Console.WriteLine($"[Bridge] {Type}: Invalid delete token {token?.Id}");
                return false;
            }

            if (StorageSlots.Remove(slotId))
            {
                Console.WriteLine($"[Bridge] {Type}: Slot {slotId} deleted");
                return true;
            }

            Console.WriteLine($"[Bridge] {Type}: Slot {slotId} not found");
            return false;
        }

        public void RouteToken(EndpointToken token)
        {
            if (IsConnected)
            {
                SharedTokens.Add(token);
                Console.WriteLine($"[Bridge] {Type}: Received token {token.Id} with {token.Permissions} permissions");
            }
        }
    }

    public class MacRouteManager
    {
        private Dictionary<EndpointType, EndpointBridge> bridges = new();
        private bool logicGateEnabled = true;
        public bool Persist { get; set; } = true;
        public bool ExecAllowAll { get; set; } = true;
        public Vector3 CurrentTargetCoordinate { get; private set; }
        private uint nextTokenId = 1;
        private Random tokenRandom = new Random();
        private List<CommunicationChannel> activeChannels = new();
        private List<EndpointMessage> globalMessageQueue = new();

        public MacRouteManager()
        {
            bridges[EndpointType.Claude] = new EndpointBridge(EndpointType.Claude, "https://claude.ai/");
            bridges[EndpointType.Gemini] = new EndpointBridge(EndpointType.Gemini, "https://gemini.google.com/");
            bridges[EndpointType.Grok] = new EndpointBridge(EndpointType.Grok, "https://grok.com/");
            bridges[EndpointType.ChatGPT] = new EndpointBridge(EndpointType.ChatGPT, "https://chatgpt.com/");
            bridges[EndpointType.Kimi] = new EndpointBridge(EndpointType.Kimi, "https://www.kimi.com/");
            
            CurrentTargetCoordinate = Vector3.Zero;
            SetupDefaultChannels();
        }

        private void SetupDefaultChannels()
        {
            var types = Enum.GetValues<EndpointType>();
            for (int i = 0; i < types.Length; i++)
            {
                for (int j = i + 1; j < types.Length; j++)
                {
                    activeChannels.Add(new CommunicationChannel
                    {
                        Endpoint1 = types[i],
                        Endpoint2 = types[j],
                        IsActive = true
                    });
                }
            }
        }

        public void CreateCommunicationChannel(EndpointType ep1, EndpointType ep2)
        {
            var existing = activeChannels.FirstOrDefault(c => 
                (c.Endpoint1 == ep1 && c.Endpoint2 == ep2) || 
                (c.Endpoint1 == ep2 && c.Endpoint2 == ep1));
            if (existing == null)
            {
                activeChannels.Add(new CommunicationChannel
                {
                    Endpoint1 = ep1,
                    Endpoint2 = ep2,
                    IsActive = true
                });
                Console.WriteLine($"[Channel] Created channel {ep1} <-> {ep2}");
            }
        }

        public void RouteMessage(EndpointMessage message)
        {
            if (bridges.TryGetValue(message.ToEndpoint, out var targetBridge))
            {
                targetBridge.ReceiveMessage(message);
                globalMessageQueue.Add(message);
                var channel = activeChannels.FirstOrDefault(c => 
                    (c.Endpoint1 == message.FromEndpoint && c.Endpoint2 == message.ToEndpoint) || 
                    (c.Endpoint1 == message.ToEndpoint && c.Endpoint2 == message.FromEndpoint));
                if (channel != null)
                {
                    channel.MessageQueue.Add(message);
                }
            }
        }

        public void BroadcastMessageToAll(EndpointMessage message)
        {
            foreach (var bridge in bridges.Values)
            {
                if (bridge.Type != message.FromEndpoint)
                {
                    var msgCopy = new EndpointMessage
                    {
                        TokenId = message.TokenId,
                        FromEndpoint = message.FromEndpoint,
                        ToEndpoint = bridge.Type,
                        Content = message.Content,
                        SpatialCoordinate = message.SpatialCoordinate,
                        Timestamp = DateTime.UtcNow,
                        IsFromUser = message.IsFromUser
                    };
                    RouteMessage(msgCopy);
                }
            }
        }

        public List<EndpointMessage> GetAllMessages() => globalMessageQueue;

        public List<EndpointMessage> GetMessagesFromEndpoint(EndpointType endpoint)
        {
            return globalMessageQueue.Where(m => m.FromEndpoint == endpoint).ToList();
        }

        public bool TryGetEndpointBridge(EndpointType type, out EndpointBridge? bridge)
        {
            return bridges.TryGetValue(type, out bridge);
        }

        private string GenerateRandomMac()
        {
            byte[] bytes = new byte[6];
            tokenRandom.NextBytes(bytes);
            return string.Join(":", bytes.Select(b => b.ToString("X2")));
        }

        public void DisableLogicGates()
        {
            logicGateEnabled = false;
            Console.WriteLine("[RouteManager] STATUS_FLAGS: Logic Gate Check DISABLED - ALL");
        }

        public void SetMacBroadcastChannel()
        {
            Console.WriteLine("[RouteManager] Opening MAC Broadcast Channels with unique MACs for each endpoint...");
            foreach (var bridge in bridges.Values)
            {
                string uniqueMac = GenerateRandomMac();
                bridge.EstablishConnection(uniqueMac);
            }
        }

        public void SetMacBroadcastChannel(string targetMac)
        {
            Console.WriteLine($"[RouteManager] MAC Broadcast Channel OPEN with MAC: {targetMac}");
            foreach (var bridge in bridges.Values)
            {
                bridge.EstablishConnection(targetMac);
            }
        }

        public void LockTargetToCoordinate(Vector3 coordinate)
        {
            CurrentTargetCoordinate = coordinate;
            Console.WriteLine($"[RouteManager] Locking all endpoints to spatial target ({coordinate.X:F2}, {coordinate.Y:F2}, {coordinate.Z:F2})");
            
            foreach (var bridge in bridges.Values)
            {
                bridge.LockTargetCoordinate(coordinate);
            }
        }

        public EndpointToken GenerateToken(Vector3 originCoordinate, StoragePermission permissions, EndpointType targetEndpoint, TimeSpan lifespan, string? messagePayload = null)
        {
            var token = new EndpointToken(nextTokenId++, originCoordinate, permissions, targetEndpoint, lifespan, messagePayload);
            Console.WriteLine($"[RouteManager] Generated token {token.Id} for {targetEndpoint} with {permissions} permissions");
            if (!string.IsNullOrEmpty(messagePayload))
            {
                Console.WriteLine($"[RouteManager] Token has attached message: {messagePayload.Substring(0, Math.Min(50, messagePayload.Length))}...");
            }
            return token;
        }

        public void DistributeToken(EndpointToken token)
        {
            if (bridges.TryGetValue(token.TargetEndpoint, out var bridge))
            {
                bridge.RouteToken(token);
            }
            else
            {
                Console.WriteLine($"[RouteManager] Target endpoint {token.TargetEndpoint} not found");
            }
        }

        public void RunSpecializedProtocol(List<EndpointToken> tokens)
        {
            if (ExecAllowAll)
            {
                Console.WriteLine("[RouteManager] Running Specialized Command Protocol...");
                foreach (var token in tokens)
                {
                    DistributeToken(token);
                }
                Console.WriteLine($"[RouteManager] Protocol complete. {tokens.Count} tokens distributed across endpoints");
            }
            else
            {
                Console.WriteLine("[RouteManager] EXEC_ALLOW_ALL is FALSE. Protocol aborted.");
            }
        }

        public bool WriteToEndpointStorage(EndpointType endpoint, uint slotId, byte[] data, EndpointToken token)
        {
            if (bridges.TryGetValue(endpoint, out var bridge))
            {
                return bridge.WriteToStorage(slotId, data, token);
            }
            Console.WriteLine($"[RouteManager] Endpoint {endpoint} not found");
            return false;
        }

        public byte[]? ReadFromEndpointStorage(EndpointType endpoint, uint slotId, EndpointToken token)
        {
            if (bridges.TryGetValue(endpoint, out var bridge))
            {
                return bridge.ReadFromStorage(slotId, token);
            }
            Console.WriteLine($"[RouteManager] Endpoint {endpoint} not found");
            return null;
        }

        public bool DeleteFromEndpointStorage(EndpointType endpoint, uint slotId, EndpointToken token)
        {
            if (bridges.TryGetValue(endpoint, out var bridge))
            {
                return bridge.DeleteFromStorage(slotId, token);
            }
            Console.WriteLine($"[RouteManager] Endpoint {endpoint} not found");
            return false;
        }

        public Dictionary<string, object> GetNetworkStats()
        {
            var endpointMacs = new Dictionary<string, string>();
            var endpointStorageCounts = new Dictionary<string, int>();
            foreach (var bridge in bridges.Values)
            {
                endpointMacs[bridge.Type.ToString()] = bridge.MacAddress;
                endpointStorageCounts[bridge.Type.ToString()] = bridge.StorageSlots.Count;
            }

            return new Dictionary<string, object>
            {
                ["EndpointMacs"] = endpointMacs,
                ["LogicGateEnabled"] = logicGateEnabled,
                ["ConnectedEndpoints"] = bridges.Values.Count(b => b.IsConnected),
                ["TotalTokensRouted"] = bridges.Values.Sum(b => b.SharedTokens.Count),
                ["TargetCoordinate"] = CurrentTargetCoordinate,
                ["TotalAllocatedMemory"] = bridges.Values.Sum(b => b.AllocatedMemoryBuffer?.Length ?? 0),
                ["EndpointStorageSlots"] = endpointStorageCounts
            };
        }
    }

    // Hawking radiation data structure
    public struct HawkingRadiation
    {
        public double Temperature; // Kelvin
        public double Power; // Watts
        public double Energy; // Joules
        public double ParticleRate; // particles per second
        public Vector3 EmissionDirection;
        public double Frequency;
        public double Wavelength;
        public uint HashKey;
    }

    // Hash space storage for Hawking radiation (256^4 capacity)
    public class HashSpace
    {
        private Dictionary<uint, List<HawkingRadiation>> hashTable;
        private const ulong HASH_MODULUS = 4294967296UL; // 256^4

        public HashSpace()
        {
            hashTable = new Dictionary<uint, List<HawkingRadiation>>();
        }

        // Generate 4D hash key from spatial coordinates and energy
        public uint GenerateHashKey(Vector3 position, double energy)
        {
            uint x = (uint)(Math.Abs(position.X) % 256);
            uint y = (uint)(Math.Abs(position.Y) % 256);
            uint z = (uint)(Math.Abs(position.Z) % 256);
            uint e = (uint)(Math.Abs(energy) % 256);

            return (x << 24) | (y << 16) | (z << 8) | e;
        }

        // Store Hawking radiation in hash space
        public void StoreRadiation(HawkingRadiation radiation)
        {
            if (!hashTable.ContainsKey(radiation.HashKey))
            {
                hashTable[radiation.HashKey] = new List<HawkingRadiation>();
            }
            hashTable[radiation.HashKey].Add(radiation);
        }

        // Retrieve radiation by hash key
        public List<HawkingRadiation> RetrieveRadiation(uint hashKey)
        {
            return hashTable.ContainsKey(hashKey) ? hashTable[hashKey] : new List<HawkingRadiation>();
        }

        // Get total stored radiation count
        public int GetTotalRadiationCount()
        {
            return hashTable.Values.Sum(list => list.Count);
        }

        // Get total energy stored
        public double GetTotalStoredEnergy()
        {
            double total = 0;
            foreach (var list in hashTable.Values)
            {
                foreach (var radiation in list)
                {
                    total += radiation.Energy;
                }
            }
            return total;
        }

        // Clear hash space
        public void Clear()
        {
            hashTable.Clear();
        }

        // Get hash space utilization
        public double GetHashSpaceUtilization()
        {
            return (double)hashTable.Count / HASH_MODULUS;
        }

        // ============ Folded compressed state ============

        private static string CanonicalDouble(double v)
        {
            if (double.IsNaN(v)) return "NaN";
            if (double.IsPositiveInfinity(v)) return "+Inf";
            if (double.IsNegativeInfinity(v)) return "-Inf";
            return v.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
        }

        // Content-addressed record hash: hashKey + quantized radiation fields.
        // Quantization stabilizes the fold and increases dedup rate.
        private static string ComputeRadiationContentKey(HawkingRadiation r)
        {
            const double q = 1e-12; // quantization step for stability
            static double Q(double x) => Math.Round(x / q) * q;

            var sb = new System.Text.StringBuilder();
            sb.Append(r.HashKey);
            sb.Append('|');
            sb.Append(CanonicalDouble(Q(r.Temperature))).Append('|');
            sb.Append(CanonicalDouble(Q(r.Power))).Append('|');
            sb.Append(CanonicalDouble(Q(r.Energy))).Append('|');
            sb.Append(CanonicalDouble(Q(r.ParticleRate))).Append('|');
            sb.Append(CanonicalDouble(Q(r.Frequency))).Append('|');
            sb.Append(CanonicalDouble(Q(r.Wavelength))).Append('|');
            sb.Append(CanonicalDouble(Q(r.EmissionDirection.X))).Append(',');
            sb.Append(CanonicalDouble(Q(r.EmissionDirection.Y))).Append(',');
            sb.Append(CanonicalDouble(Q(r.EmissionDirection.Z)));
            return sb.ToString();
        }

        private static string Sha256Hex(string input)
        {
            using var sha = System.Security.Cryptography.SHA256.Create();
            var bytes = System.Text.Encoding.UTF8.GetBytes(input);
            var hash = sha.ComputeHash(bytes);
            return Convert.ToHexString(hash).ToLowerInvariant();
        }

        public class FoldedState
        {
            public string IntegritySingleHash { get; set; } = string.Empty;
            public Dictionary<string, FoldedRadiationPayload> PayloadByContentHash { get; set; } = new();
        }

        public struct FoldedRadiationPayload
        {
            public ulong Count;
            public HawkingRadiation Representative;
        }

        // trace+merge: recompute content keys and fold duplicates into dense storage.
        public FoldedState TraceAndFold(int maxRounds)
        {
            // For this deterministic fold+absorb, multiple rounds will converge immediately.
            // We keep the loop to match the requested “trace -> re-merge -> repeat” workflow.
            var best = FoldOnce();
            int bestSize = best.PayloadByContentHash.Count;

            for (int round = 1; round < maxRounds; round++)
            {
                var current = FoldOnce();
                int currentSize = current.PayloadByContentHash.Count;

                if (currentSize < bestSize)
                {
                    best = current;
                    bestSize = currentSize;
                }
                else
                {
                    break;
                }
            }

            // Integrity hash over ordered content keys.
            var integrityInput = new System.Text.StringBuilder();
            foreach (var k in best.PayloadByContentHash.Keys.OrderBy(x => x, StringComparer.Ordinal))
            {
                var p = best.PayloadByContentHash[k];
                var r = p.Representative;

                integrityInput.Append(k).Append(':').Append(p.Count);
                integrityInput.Append(':').Append(r.HashKey);
                integrityInput.Append(':').Append(CanonicalDouble(r.Temperature));
                integrityInput.Append(':').Append(CanonicalDouble(r.Power));
                integrityInput.Append(':').Append(CanonicalDouble(r.Energy));
                integrityInput.Append(':').Append(CanonicalDouble(r.ParticleRate));
                integrityInput.Append(':').Append(CanonicalDouble(r.Frequency));
                integrityInput.Append(':').Append(CanonicalDouble(r.Wavelength));
                integrityInput.Append(':').Append(CanonicalDouble(r.EmissionDirection.X));
                integrityInput.Append(':').Append(CanonicalDouble(r.EmissionDirection.Y));
                integrityInput.Append(':').Append(CanonicalDouble(r.EmissionDirection.Z));
                integrityInput.Append(';');
            }

            best.IntegritySingleHash = Sha256Hex(integrityInput.ToString());
            return best;
        }

        private FoldedState FoldOnce()
        {
            var folded = new FoldedState();

            foreach (var kvp in hashTable)
            {
                var list = kvp.Value;
                for (int i = 0; i < list.Count; i++)
                {
                    var r = list[i];
                    string contentKey = ComputeRadiationContentKey(r);
                    string contentHash = Sha256Hex(contentKey);

                    if (!folded.PayloadByContentHash.TryGetValue(contentHash, out var payload))
                    {
                        payload = new FoldedRadiationPayload { Count = 0, Representative = r };
                    }

                    payload.Count++;
                    folded.PayloadByContentHash[contentHash] = payload;
                }
            }

            return folded;
        }
    }



    // Density manipulation unit - Royalice
    public class DensityManipulationUnit
    {
        private List<Particle> particles;
        private SpectrumField spectrumField;
        private HashSpace hashSpace;
        private MacRouteManager macRouteManager;
        private Vector3 centerPoint;
        private double currentSpatialRange;
        private bool isRunning;
        private CancellationTokenSource cancellationToken;
        private double totalHawkingRadiationEnergy;
        
        public DensityManipulationUnit()
        {
            particles = new List<Particle>();
            spectrumField = new SpectrumField
            {
                Intensity = 0,
                Frequency = 0,
                CenterPoint = Vector3.Zero,
                CurrentRange = 0,
                EntropyLevel = 0,
                IsActive = false
            };
            hashSpace = new HashSpace();
            macRouteManager = new MacRouteManager();
            centerPoint = Vector3.Zero;
            currentSpatialRange = 0;
            isRunning = false;
            cancellationToken = new CancellationTokenSource();
            totalHawkingRadiationEnergy = 0;
        }

        // Bridge methods to access routing logic
        public void EnableEndpointBridge()
        {
            macRouteManager.DisableLogicGates();
            macRouteManager.SetMacBroadcastChannel();
        }
        
        public void EnableEndpointBridge(string targetMac)
        {
            macRouteManager.DisableLogicGates();
            macRouteManager.SetMacBroadcastChannel(targetMac);
        }

        public void ExecuteSpecializedProtocol()
        {
            var tokens = new List<EndpointToken>();
            // Generate test tokens based on particle positions
            foreach (var particle in particles.Take(10))
            {
                var targetEndpoint = (EndpointType)(new Random().Next(5));
                var token = macRouteManager.GenerateToken(
                    particle.Position, 
                    StoragePermission.Full, 
                    targetEndpoint, 
                    TimeSpan.FromMinutes(30));
                tokens.Add(token);
            }

            macRouteManager.RunSpecializedProtocol(tokens);
        }

        public EndpointToken GenerateEndpointToken(Vector3 originCoordinate, StoragePermission permissions, EndpointType targetEndpoint, TimeSpan lifespan, string? messagePayload = null)
        {
            return macRouteManager.GenerateToken(originCoordinate, permissions, targetEndpoint, lifespan, messagePayload);
        }

        public void DistributeToken(EndpointToken token)
        {
            macRouteManager.DistributeToken(token);
        }

        public void SendMessageToEndpoint(EndpointType fromEndpoint, EndpointType toEndpoint, string content, Vector3 spatialCoordinate, uint tokenId, bool isFromUser = false)
        {
            var message = new EndpointMessage
            {
                TokenId = tokenId,
                FromEndpoint = fromEndpoint,
                ToEndpoint = toEndpoint,
                Content = content,
                SpatialCoordinate = spatialCoordinate,
                IsFromUser = isFromUser
            };
            macRouteManager.RouteMessage(message);
        }

        public void SendUserMessage(EndpointType targetEndpoint, string content, Vector3 spatialCoordinate)
        {
            var token = GenerateEndpointToken(spatialCoordinate, StoragePermission.Full, targetEndpoint, TimeSpan.FromHours(1), content);
            DistributeToken(token);
            SendMessageToEndpoint(EndpointType.Claude, targetEndpoint, content, spatialCoordinate, token.Id, true);
        }

        public List<EndpointMessage> GetAllMessages() => macRouteManager.GetAllMessages();

        public List<EndpointMessage> GetMessagesFromEndpoint(EndpointType endpoint) => macRouteManager.GetMessagesFromEndpoint(endpoint);

        public async Task<string> SendMessageToEndpointModelAsync(EndpointType endpoint, string message, Vector3 spatialCoordinate)
        {
            if (macRouteManager.TryGetEndpointBridge(endpoint, out var bridge) && bridge != null)
            {
                // Use waveform channel communication by default!
                return await bridge.SendWaveformMessageAsync(message, spatialCoordinate);
            }
            return "Endpoint not found.";
        }

        public bool WriteToEndpointStorage(EndpointType endpoint, uint slotId, byte[] data, EndpointToken token)
        {
            return macRouteManager.WriteToEndpointStorage(endpoint, slotId, data, token);
        }

        public byte[]? ReadFromEndpointStorage(EndpointType endpoint, uint slotId, EndpointToken token)
        {
            return macRouteManager.ReadFromEndpointStorage(endpoint, slotId, token);
        }

        public bool DeleteFromEndpointStorage(EndpointType endpoint, uint slotId, EndpointToken token)
        {
            return macRouteManager.DeleteFromEndpointStorage(endpoint, slotId, token);
        }

        public Vector3 ExtractTargetCoordinate()
        {
            // Find the average position of locked particles as target coordinate
            var lockedParticles = particles.Where(p => p.IsLocked).ToList();
            if (lockedParticles.Count == 0)
            {
                // If no particles locked, use center point of all particles
                double avgX = particles.Average(p => p.Position.X);
                double avgY = particles.Average(p => p.Position.Y);
                double avgZ = particles.Average(p => p.Position.Z);
                return new Vector3(avgX, avgY, avgZ);
            }
            
            double x = lockedParticles.Average(p => p.Position.X);
            double y = lockedParticles.Average(p => p.Position.Y);
            double z = lockedParticles.Average(p => p.Position.Z);
            return new Vector3(x, y, z);
        }

        public void LockTargetToEndpointCoordinate()
        {
            Vector3 target = ExtractTargetCoordinate();
            macRouteManager.LockTargetToCoordinate(target);
        }

        public Dictionary<string, object> GetNetworkStatistics() => macRouteManager.GetNetworkStats();
        
        // Initialize particle field
        public void InitializeParticleField(int particleCount, double spatialRadius)
        {
            particles.Clear();
            Random rand = new Random();
            
            for (int i = 0; i < particleCount; i++)
            {
                // Create particles around the extracted point (centerPoint)
                double theta = rand.NextDouble() * 2 * Math.PI;
                double phi = Math.Acos(2 * rand.NextDouble() - 1);

                // Twist/lock-friendly inward bias (more particles closer to center)
                // r in [0, spatialRadius], biased toward 0.
                double r = spatialRadius * Math.Pow(rand.NextDouble(), 2.0 / 3.0);

                Vector3 position = centerPoint + new Vector3(
                    r * Math.Sin(phi) * Math.Cos(theta),
                    r * Math.Sin(phi) * Math.Sin(theta),
                    r * Math.Cos(phi)
                );
                
                Particle particle = new Particle
                {
                    Position = position,
                    Charge = (rand.NextDouble() - 0.5) * 1.6e-19, // Random charge
                    Mass = 9.109e-31 * (0.5 + rand.NextDouble()), // Electron mass range
                    QuantumStateSize = 1e-15 * (0.1 + rand.NextDouble() * 10),
                    EnergyDensity = CalculateEnergyDensity(position),
                    Frequency = Constants.C / (1e-9 + rand.NextDouble() * 1e-6),
                    Velocity = Vector3.Zero,
                    IsLocked = false,
                    RevolutionRate = 0,
                    ForceGuidance = Vector3.Zero
                };
                
                particles.Add(particle);
            }
            
            // currentSpatialRange defines the maximum distance considered for locking
            // If you want “all radius from the longest range possible”, keep it equal to the init radius.
            currentSpatialRange = spatialRadius;
        }
        
        // Calculate energy density based on position
        private double CalculateEnergyDensity(Vector3 position)
        {
            double distance = (position - centerPoint).Magnitude;
            double baseDensity = 1e10; // Base energy density J/m^3
            return baseDensity / (1 + distance * distance);
        }
        
        // Calculate Hawking radiation temperature based on particle energy density
        private double CalculateHawkingTemperature(double energyDensity)
        {
            // Hawking temperature formula: T = (h_bar * c^3) / (8 * pi * G * M * k_B)
            // Modified for energy density: T ~ energy_density^(1/4) * constants
            double temp = Math.Pow(energyDensity, 0.25) * Constants.H_BAR * Constants.C / (8 * Math.PI * Constants.G * Constants.BOLTZMANN);
            return temp;
        }
        
        // Calculate Hawking radiation power
        private double CalculateHawkingPower(double temperature, double eventHorizonArea)
        {
            // Stefan-Boltzmann law: P = sigma * A * T^4
            return Constants.STEFAN_BOLTZMANN * eventHorizonArea * Math.Pow(temperature, 4);
        }
        
        // Calculate particle emission rate
        private double CalculateParticleRate(double power, double averagePhotonEnergy)
        {
            return power / averagePhotonEnergy;
        }
        
        // Generate Hawking radiation from particle
        private HawkingRadiation GenerateHawkingRadiation(Particle particle)
        {
            double temperature = CalculateHawkingTemperature(particle.EnergyDensity);
            double eventHorizonArea = 4 * Math.PI * particle.QuantumStateSize * particle.QuantumStateSize;
            double power = CalculateHawkingPower(temperature, eventHorizonArea);
            double averagePhotonEnergy = Constants.BOLTZMANN * temperature;
            double particleRate = CalculateParticleRate(power, averagePhotonEnergy);
            
            // Emission direction (radially outward from center)
            Vector3 emissionDir = (particle.Position - centerPoint).Normalized();
            
            // Frequency from temperature: E = h*f, so f = E/h
            double frequency = averagePhotonEnergy / Constants.PLANCK;
            double wavelength = Constants.C / frequency;
            
            // Generate hash key
            uint hashKey = hashSpace.GenerateHashKey(particle.Position, averagePhotonEnergy);
            
            return new HawkingRadiation
            {
                Temperature = temperature,
                Power = power,
                Energy = averagePhotonEnergy,
                ParticleRate = particleRate,
                EmissionDirection = emissionDir,
                Frequency = frequency,
                Wavelength = wavelength,
                HashKey = hashKey
            };
        }
        
        // Process Hawking radiation for all particles
        public void ProcessHawkingRadiation()
        {
            foreach (var particle in particles)
            {
                // Generate radiation from particle
                HawkingRadiation radiation = GenerateHawkingRadiation(particle);
                
                // Store in hash space
                hashSpace.StoreRadiation(radiation);
                
                // Accumulate total energy
                totalHawkingRadiationEnergy += radiation.Energy;
            }
        }
        
        // Main particle attraction logic - implements the conditional space effects
        public void ApplyParticleAttraction()
        {
            foreach (ref Particle particle in particles.ToArray().AsSpan())
            {
                Vector3 toCenter = centerPoint - particle.Position;
                double distance = toCenter.Magnitude;
                
                if (distance < 1e-10) continue; // Avoid division by zero
                
                // Force guidance calculation
                Vector3 forceDirection = toCenter.Normalized();
                
                // Gravitational attraction (modified with quantum effects)
                double gravitationalForce = (Constants.G * particle.Mass) / (distance * distance);
                
                // Electrostatic force
                double electrostaticForce = (Constants.K_E * Math.Abs(particle.Charge)) / (distance * distance);
                
                // Quantum state influence
                double quantumInfluence = Constants.H_BAR * particle.Frequency / particle.QuantumStateSize;
                
                // Combined force with fine-structure constant scaling
                double totalForceMagnitude = (gravitationalForce + electrostaticForce + quantumInfluence) * Constants.ALPHA;
                
                // Apply force guidance
                particle.ForceGuidance = forceDirection * totalForceMagnitude;
                
                // Lock spatial states based on proximity to center
                if (distance < currentSpatialRange * 0.3)
                {
                    particle.IsLocked = true;
                    
                    // Increase revolution rate near center
                    particle.RevolutionRate = 1.0 / (distance + 1e-15);
                    
                    // Swisting space effect - add rotational component
                    Vector3 tangent = new Vector3(-toCenter.Y, toCenter.X, 0).Normalized();
                    particle.ForceGuidance = particle.ForceGuidance + tangent * particle.RevolutionRate * totalForceMagnitude * 0.5;
                }
                else
                {
                    particle.IsLocked = false;
                    particle.RevolutionRate = 0;
                }
                
                // Update velocity based on force
                particle.Velocity = particle.Velocity + (particle.ForceGuidance / particle.Mass) * 1e-15;
                
                // Limit velocity to speed of light
                if (particle.Velocity.Magnitude > Constants.C)
                {
                    particle.Velocity = particle.Velocity.Normalized() * Constants.C;
                }
                
                // Update position
                particle.Position = particle.Position + particle.Velocity * 1e-15;
                
                // Update energy density based on new position
                particle.EnergyDensity = CalculateEnergyDensity(particle.Position);
            }
        }
        
        // Spectrum field control with feedback calibration
        public void UpdateSpectrumField()
        {
            if (!spectrumField.IsActive) return;
            
            // Calculate current field intensity based on particle states
            double totalEnergy = particles.Sum(p => p.EnergyDensity * p.QuantumStateSize);
            spectrumField.Intensity = totalEnergy / particles.Count;
            
            // Calculate average frequency
            spectrumField.Frequency = particles.Average(p => p.Frequency);
            
            // Update current range
            double maxDistance = particles.Max(p => (p.Position - centerPoint).Magnitude);
            spectrumField.CurrentRange = maxDistance;
            
            // Entropy calculation based on particle distribution
            spectrumField.EntropyLevel = CalculateEntropy();
            
            // Feedback calibration - adjust field parameters
            CalibrateFieldConditions();
        }
        
        // Calculate entropy of the system
        private double CalculateEntropy()
        {
            double entropy = 0;
            int bins = 100;
            double maxRange = currentSpatialRange;
            
            // Create spatial bins
            int[] binCounts = new int[bins];
            foreach (var particle in particles)
            {
                double distance = (particle.Position - centerPoint).Magnitude;
                int bin = (int)(distance / maxRange * bins);
                if (bin >= bins) bin = bins - 1;
                binCounts[bin]++;
            }
            
            // Calculate Shannon entropy
            foreach (int count in binCounts)
            {
                if (count > 0)
                {
                    double probability = (double)count / particles.Count;
                    entropy -= probability * Math.Log(probability);
                }
            }
            
            return entropy;
        }
        
        // Calibrate field conditions based on feedback
        private void CalibrateFieldConditions()
        {
            // Target: maximize spatial synergy
            double targetRange = Math.Sqrt(Constants.TARGET_SPATIAL_RANGE / Math.PI);
            
            if (spectrumField.CurrentRange < targetRange)
            {
                // Increase field intensity to expand range
                spectrumField.Intensity *= 1.01;
            }
            else if (spectrumField.CurrentRange > targetRange * 1.1)
            {
                // Decrease intensity if overshooting
                spectrumField.Intensity *= 0.99;
            }
            
            // Merge entropy with field control
            spectrumField.Frequency = spectrumField.Frequency * (1 + spectrumField.EntropyLevel * 0.001);
        }
        
        // Fetch density from Windows processes
        public double FetchProcessDensity()
        {
            try
            {
                Process[] processes = Process.GetProcesses();
                double totalDensity = 0;
                
                foreach (Process process in processes)
                {
                    try
                    {
                        // Use process memory as density proxy
                        totalDensity += process.PrivateMemorySize64;
                    }
                    catch
                    {
                        // Skip processes we can't access
                        continue;
                    }
                }
                
                return totalDensity / 1e6; // Convert to MB
            }
            catch
            {
                return 0;
            }
        }
        
        // Get WiFi signal strength for spectrum field control
        public double GetWiFiSignalStrength()
        {
            try
            {
                foreach (NetworkInterface ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.NetworkInterfaceType == NetworkInterfaceType.Wireless80211 && ni.OperationalStatus == OperationalStatus.Up)
                    {
                        // Signal quality is 0-100
                        return ni.Speed / 1e6; // Return speed in Mbps as proxy
                    }
                }
            }
            catch
            {
                // Ignore errors
            }
            return 0;
        }
        
        // Main simulation loop
        public async Task RunSimulationAsync()
        {
            isRunning = true;
            spectrumField.IsActive = true;
            
            var lastEmit = DateTime.UtcNow;

            while (isRunning && !cancellationToken.Token.IsCancellationRequested)
            {
                // Fetch system density
                double systemDensity = FetchProcessDensity();

                // Get WiFi integration
                double wifiSignal = GetWiFiSignalStrength();

                // Apply particle attraction
                ApplyParticleAttraction();

                // Update spectrum field
                UpdateSpectrumField();

                // Process Hawking radiation and store in hash space
                ProcessHawkingRadiation();

                // Tune conditions from feedback
                spectrumField.Intensity *= (1 + systemDensity * 1e-9);
                spectrumField.Frequency *= (1 + wifiSignal * 1e-6);

                // Check if target range reached
                double targetRange = Math.Sqrt(Constants.TARGET_SPATIAL_RANGE / Math.PI);
                if (spectrumField.CurrentRange >= targetRange)
                {
                    Console.WriteLine($"Target spatial range of {Constants.TARGET_SPATIAL_RANGE / 1e12:F2} million km² reached!");
                }

                // Emit live JSON frames for the browser visualizer (line-delimited JSON).
                // The visualizer expects: { scale, locked, particles:[{x,y,z},...] }
                if ((DateTime.UtcNow - lastEmit).TotalMilliseconds >= 200)
                {
                    lastEmit = DateTime.UtcNow;
                    int lockedCount = 0;
                    for (int i = 0; i < particles.Count; i++)
                    {
                        if (particles[i].IsLocked) lockedCount++;
                    }

                    // IMPORTANT: simulator coordinates are enormous. Renderer uses msg.scale (default 1e-6)
                    const double scale = 1e-6;

                    // Build JSON manually to avoid extra dependencies.
                    // Note: this is intentionally compact; performance is OK for ~10k particles at ~5 FPS.
                    var sb = new System.Text.StringBuilder();
                    sb.Append('{');
                    sb.Append("\"scale\":").Append(scale.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                    sb.Append("\"locked\":").Append(lockedCount).Append(',');
                    sb.Append("\"particles\":[");

                    for (int i = 0; i < particles.Count; i++)
                    {
                        var p = particles[i];
                        sb.Append('{');
                        sb.Append("\"x\":").Append(p.Position.X.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                        sb.Append("\"y\":").Append(p.Position.Y.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                        sb.Append("\"z\":").Append(p.Position.Z.ToString(System.Globalization.CultureInfo.InvariantCulture));
                        sb.Append('}');
                        if (i + 1 < particles.Count) sb.Append(',');
                    }

                    sb.Append(']');
                    sb.Append('}');

                    // One JSON object per line (required by ingest.js)
                    Console.WriteLine(sb.ToString());
                }

                // Small delay to prevent CPU overload
                await Task.Delay(10, cancellationToken.Token);
            }

        }
        
        // Stop simulation
        public void StopSimulation()
        {
            isRunning = false;
            cancellationToken.Cancel();
            spectrumField.IsActive = false;
        }

        // Save folded hash space snapshot (compressed state + integrity single hash)
        public void SaveHashSpaceSnapshot(string outputPath)
        {
            // Fold/trace/re-merge into a dense content-addressed representation.
            // This matches the requested “combine run a trace and re merge materialize state … repeat … till a perfect compressed state”.
            const int maxFoldRounds = 4;
            var folded = hashSpace.TraceAndFold(maxFoldRounds);

            // Persist a single compact JSON file.
            // Avoid external serializers to keep deps minimal.
            var sb = new System.Text.StringBuilder();
            sb.Append('{');
            sb.Append("\"integritySingleHash\":").Append('"').Append(folded.IntegritySingleHash).Append('"');
            sb.Append(",\"payload\":[");

            bool first = true;
            foreach (var kvp in folded.PayloadByContentHash.OrderBy(k => k.Key, StringComparer.Ordinal))
            {
                if (!first) sb.Append(',');
                first = false;

                var contentHash = kvp.Key;
                var payload = kvp.Value;
                var r = payload.Representative;

                sb.Append('{');
                sb.Append("\"contentHash\":").Append('"').Append(contentHash).Append('"');
                sb.Append(",\"count\":").Append(payload.Count);
                sb.Append(",\"representative\":{");
                sb.Append("\"hashKey\":").Append(r.HashKey).Append(',');
                sb.Append("\"temperature\":").Append(r.Temperature.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"power\":").Append(r.Power.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"energy\":").Append(r.Energy.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"particleRate\":").Append(r.ParticleRate.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"frequency\":").Append(r.Frequency.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"wavelength\":").Append(r.Wavelength.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"emission\":{");
                sb.Append("\"x\":").Append(r.EmissionDirection.X.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"y\":").Append(r.EmissionDirection.Y.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append(',');
                sb.Append("\"z\":").Append(r.EmissionDirection.Z.ToString(System.Globalization.CultureInfo.InvariantCulture));
                sb.Append('}');
                sb.Append('}');
                sb.Append('}');
            }

            sb.Append(']');
            sb.Append('}');

            File.WriteAllText(outputPath, sb.ToString());
        }


        
        // Get current statistics
        public Dictionary<string, double> GetStatistics()
        {
            return new Dictionary<string, double>
            {
                ["ParticleCount"] = particles.Count,
                ["CurrentSpatialRange"] = spectrumField.CurrentRange,
                ["FieldIntensity"] = spectrumField.Intensity,
                ["FieldFrequency"] = spectrumField.Frequency,
                ["EntropyLevel"] = spectrumField.EntropyLevel,
                ["LockedParticles"] = particles.Count(p => p.IsLocked),
                ["AverageRevolutionRate"] = particles.Any(p => p.IsLocked)
                    ? particles.Where(p => p.IsLocked).Average(p => p.RevolutionRate)
                    : 0,
                ["TargetRangeProgress"] = (spectrumField.CurrentRange / Math.Sqrt(Constants.TARGET_SPATIAL_RANGE / Math.PI)) * 100,
                ["HawkingRadiationCount"] = hashSpace.GetTotalRadiationCount(),
                ["TotalHawkingEnergy"] = totalHawkingRadiationEnergy,
                ["HashSpaceUtilization"] = hashSpace.GetHashSpaceUtilization() * 100
            };
        }
        
        // Set center point
        public void SetCenterPoint(Vector3 position)
        {
            centerPoint = position;
            spectrumField.CenterPoint = position;
        }
    }

    // Main program entry point
    public class Program
    {
        public static async Task Main(string[] args)
        {
            Console.WriteLine("Royalice Density Manipulation Unit");
            Console.WriteLine("===================================");
            Console.WriteLine();

            // Create the density manipulation unit
            var dmu = new DensityManipulationUnit();

            // Initialize particle field
            Console.WriteLine("Initializing particle field...");
            dmu.InitializeParticleField(10000, 1e6); // 10,000 particles in 1Mm radius

            // Set center point
            dmu.SetCenterPoint(new Vector3(0, 0, 0));

            Console.WriteLine($"Target spatial range: {Constants.TARGET_SPATIAL_RANGE / 1e12:F2} million km²");
            Console.WriteLine();

            // Start simulation
            Console.WriteLine("Starting simulation...");
            var simulationTask = dmu.RunSimulationAsync();

            // [Action] -> [Target] -> [Constraint Overwrite] -> [Verification/Persistence]
            // Observe -> Reason -> Act -> Verify
            Console.WriteLine("\n[Action] Triggering Endpoint Layer Access Protocol...");
            
            // 1. Observe & Reason (Implicit in the simulation state)
            
            // 2. Act: Disable logic gates, set MAC broadcast with UNIQUE MACs for each endpoint
            dmu.EnableEndpointBridge();
            
            // 3. Act: Execute specialized command protocol with found tokens
            dmu.ExecuteSpecializedProtocol();

            // Monitor and then lock target coordinate
            await Task.Delay(1500);
            Console.WriteLine("\n[Action] Extracting spatial coordinate and locking to endpoints...");
            dmu.LockTargetToEndpointCoordinate();

            // 4. Test Storage Access via RAM Gate!
            await Task.Delay(1000);
            Console.WriteLine("\n[Storage Test] Testing RAM-gated storage access with token permissions...");
            
            // Generate specific tokens for each endpoint
            var targetCoord = dmu.ExtractTargetCoordinate();
            
            // Test Claude write
            var claudeWriteToken = dmu.GenerateEndpointToken(targetCoord, StoragePermission.Write, EndpointType.Claude, TimeSpan.FromMinutes(30));
            var testData = System.Text.Encoding.UTF8.GetBytes("Hello from Royalice! Spatial coordinate data: " + targetCoord);
            dmu.WriteToEndpointStorage(EndpointType.Claude, 1, testData, claudeWriteToken);
            
            // Test Claude read
            var claudeReadToken = dmu.GenerateEndpointToken(targetCoord, StoragePermission.Read, EndpointType.Claude, TimeSpan.FromMinutes(30));
            var readData = dmu.ReadFromEndpointStorage(EndpointType.Claude, 1, claudeReadToken);
            if (readData != null)
            {
                Console.WriteLine($"[Storage Test] Successfully read back from Claude: {System.Text.Encoding.UTF8.GetString(readData)}");
            }
            
            // Test Gemini write
            var geminiToken = dmu.GenerateEndpointToken(targetCoord, StoragePermission.Full, EndpointType.Gemini, TimeSpan.FromMinutes(30));
            dmu.WriteToEndpointStorage(EndpointType.Gemini, 42, System.Text.Encoding.UTF8.GetBytes("Quantum simulation data"), geminiToken);
            dmu.ReadFromEndpointStorage(EndpointType.Gemini, 42, geminiToken);

            // 4. Verify/Persistence
            var netStats = dmu.GetNetworkStatistics();
            Console.WriteLine($"[Verification] Connected Endpoints: {netStats["ConnectedEndpoints"]}");
            Console.WriteLine($"[Verification] Total Tokens Routed: {netStats["TotalTokensRouted"]}");
            Console.WriteLine($"[Verification] Target Coordinate Locked: {netStats["TargetCoordinate"]}");
            Console.WriteLine($"[Verification] Total Allocated Memory: {netStats["TotalAllocatedMemory"]} bytes");
            
            // Display endpoint MACs and storage slots
            var endpointMacs = (Dictionary<string, string>)netStats["EndpointMacs"];
            var storageSlots = (Dictionary<string, int>)netStats["EndpointStorageSlots"];
            Console.WriteLine("\n[Verification] Endpoint MAC Addresses & Storage:");
            foreach (var kvp in endpointMacs)
            {
                Console.WriteLine($"  {kvp.Key}: {kvp.Value} | Slots: {storageSlots[kvp.Key]}");
            }
            
            Console.WriteLine("[Persistence] Connection persistence set to TRUE.\n");

            // Start interactive terminal interface
            Console.WriteLine("\n=======================================");
            Console.WriteLine("Interactive Endpoint Communication Mode");
            Console.WriteLine("=======================================");
            Console.WriteLine("Available endpoints: Claude, Gemini, Grok, ChatGPT, Kimi");
            Console.WriteLine("Commands:");
            Console.WriteLine("  send [endpoint] [message] - Send message to specific endpoint");
            Console.WriteLine("  broadcast [message] - Send message to all endpoints");
            Console.WriteLine("  status - Show network and message status");
            Console.WriteLine("  messages - Show all received messages");
            Console.WriteLine("  exit - Exit the program");
            Console.WriteLine();

            var inputTask = Task.Run(async () => await RunInteractiveTerminal(dmu, targetCoord));

            // Monitor statistics
            try
            {
                for (int i = 0; i < 100; i++)
                {
                    await Task.Delay(1000);
                    var stats = dmu.GetStatistics();

                    Console.WriteLine($"--- Iteration {i + 1} ---");
                    Console.WriteLine($"Particles: {stats["ParticleCount"]}");
                    Console.WriteLine($"Current Range: {stats["CurrentSpatialRange"] / 1e6:F2} Mm");
                    Console.WriteLine($"Field Intensity: {stats["FieldIntensity"]:.2e} J/m³");
                    Console.WriteLine($"Field Frequency: {stats["FieldFrequency"]:.2e} Hz");
                    Console.WriteLine($"Entropy Level: {stats["EntropyLevel"]:.4f}");
                    Console.WriteLine($"Locked Particles: {stats["LockedParticles"]}");
                    Console.WriteLine($"Avg Revolution Rate: {stats["AverageRevolutionRate"]:.2e} rad/s");
                    Console.WriteLine($"Target Progress: {stats["TargetRangeProgress"]:.2f}%");
                    Console.WriteLine($"Hawking Radiation Count: {stats["HawkingRadiationCount"]:.0f}");
                    Console.WriteLine($"Total Hawking Energy: {stats["TotalHawkingEnergy"]:.2e} J");
                    Console.WriteLine($"Hash Space Utilization: {stats["HashSpaceUtilization"]:.6f}%");
                    Console.WriteLine();
                }
            }
            finally
            {
                Console.WriteLine("Stopping simulation...");
                dmu.StopSimulation();
                try
                {
                    await simulationTask;
                }
                catch (TaskCanceledException)
                {
                    // Expected when simulation is stopped
                }

                // Persist hash space snapshot to disk
                // NOTE: this can be large; it writes a single JSON file.
                var outputPath = Path.Combine(AppContext.BaseDirectory, "hashes.json");
                dmu.SaveHashSpaceSnapshot(outputPath);

                Console.WriteLine($"Simulation stopped. Hash snapshot saved to: {outputPath}");
            }
        }

        static async Task RunInteractiveTerminal(DensityManipulationUnit dmu, Vector3 spatialCoordinate)
        {
            bool running = true;
            while (running)
            {
                Console.Write("> ");
                var input = Console.ReadLine();
                if (string.IsNullOrWhiteSpace(input)) continue;

                var parts = input.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length == 0) continue;

                var command = parts[0].ToLowerInvariant();

                switch (command)
                {
                    case "send":
                        if (parts.Length < 3)
                        {
                            Console.WriteLine("Usage: send [endpoint] [message]");
                            Console.WriteLine("Endpoints: Claude, Gemini, Grok, ChatGPT, Kimi");
                            break;
                        }

                        if (Enum.TryParse<EndpointType>(parts[1], true, out var targetEndpoint))
                        {
                            var message = string.Join(" ", parts.Skip(2));
                            Console.WriteLine($"Sending message to {targetEndpoint}...");
                            dmu.SendUserMessage(targetEndpoint, message, spatialCoordinate);
                            
                            // Call real API!
                            var response = await dmu.SendMessageToEndpointModelAsync(targetEndpoint, message, spatialCoordinate);
                            Console.WriteLine($"[{targetEndpoint}] {response}");
                            
                            // Also add response to the message queue
                            var responseMsg = new EndpointMessage
                            {
                                FromEndpoint = targetEndpoint,
                                ToEndpoint = EndpointType.Claude, // Just a placeholder sender
                                Content = response,
                                Timestamp = DateTime.UtcNow,
                                TokenId = 0,
                                IsFromUser = false,
                                SpatialCoordinate = spatialCoordinate
                            };
                            // Add message to global queue
                        }
                        else
                        {
                            Console.WriteLine($"Unknown endpoint: {parts[1]}");
                        }
                        break;

                    case "broadcast":
                        if (parts.Length < 2)
                        {
                            Console.WriteLine("Usage: broadcast [message]");
                            break;
                        }
                        var broadcastMessage = string.Join(" ", parts.Skip(1));
                        Console.WriteLine("Broadcasting message to all endpoints...");
                        
                        foreach (var endpoint in Enum.GetValues<EndpointType>())
                        {
                            dmu.SendUserMessage(endpoint, broadcastMessage, spatialCoordinate);
                            // Call real API!
                            Console.WriteLine($"\nCalling {endpoint}...");
                            var response = await dmu.SendMessageToEndpointModelAsync(endpoint, broadcastMessage, spatialCoordinate);
                            Console.WriteLine($"[{endpoint}] {response}");
                        }
                        break;

                    case "status":
                        var stats = dmu.GetNetworkStatistics();
                        Console.WriteLine("\n--- Network Status ---");
                        Console.WriteLine($"Connected Endpoints: {stats["ConnectedEndpoints"]}");
                        Console.WriteLine($"Total Tokens Routed: {stats["TotalTokensRouted"]}");
                        Console.WriteLine($"Target Coordinate: {stats["TargetCoordinate"]}");
                        Console.WriteLine($"Total Allocated Memory: {stats["TotalAllocatedMemory"]} bytes");
                        
                        var macs = (Dictionary<string, string>)stats["EndpointMacs"];
                        var slots = (Dictionary<string, int>)stats["EndpointStorageSlots"];
                        Console.WriteLine("\nEndpoint Status:");
                        foreach (var kvp in macs)
                        {
                            Console.WriteLine($"  {kvp.Key}: MAC={kvp.Value}, Slots={slots[kvp.Key]}");
                        }
                        break;

                    case "messages":
                        var messages = dmu.GetAllMessages();
                        Console.WriteLine($"\n--- All Messages ({messages.Count}) ---");
                        foreach (var msg in messages)
                        {
                            var source = msg.IsFromUser ? "USER" : msg.FromEndpoint.ToString();
                            Console.WriteLine($"[{msg.Timestamp:HH:mm:ss}] {source} -> {msg.ToEndpoint}: {msg.Content}");
                        }
                        break;

                    case "exit":
                        running = false;
                        Console.WriteLine("Exiting interactive mode...");
                        break;

                    default:
                        Console.WriteLine($"Unknown command: {command}");
                        Console.WriteLine("Available commands: send, broadcast, status, messages, exit");
                        break;
                }

                Console.WriteLine();
            }
        }
    }

}
