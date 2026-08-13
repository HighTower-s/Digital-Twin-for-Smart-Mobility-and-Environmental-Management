using System;
using SocketIOClient;
using UnityEngine;

namespace SmartFlow.Network
{
    // Standalone connection test — attach to any empty GameObject to verify the
    // backend is reachable and print every "spawn_vehicle" payload it broadcasts.
    // Does not touch VehiclePool; this is for manual verification only.
    public class SpawnVehicleTestClient : MonoBehaviour
    {
        [SerializeField] private string _serverUrl = "http://localhost:3000";

        private SocketIOUnity _socket;

        private void Start()
        {
            Connect();
        }

        private void Connect()
        {
            var uri = new Uri(_serverUrl);
            _socket = new SocketIOUnity(uri, new SocketIOOptions
            {
                Reconnection = true,
                ReconnectionAttempts = int.MaxValue,
                ReconnectionDelay = 3000,
            });

            _socket.OnConnected += (_, _) =>
                Debug.Log($"[SpawnVehicleTestClient] Connected to {_serverUrl}");

            _socket.OnDisconnected += (_, reason) =>
                Debug.LogWarning($"[SpawnVehicleTestClient] Disconnected: {reason}");

            _socket.OnError += (_, error) =>
                Debug.LogError($"[SpawnVehicleTestClient] Error: {error}");

            _socket.OnUnityThread("spawn_vehicle", response =>
            {
                // GetValue<T>() uses System.Text.Json which skips public fields.
                // Extract raw JSON and use JsonUtility which handles [Serializable] fields.
                // (Same workaround as WebSocketClient.cs — see docs/bug-log.md BUG-002.)
                string json;
                try
                {
                    json = response.GetValue<System.Text.Json.JsonElement>().GetRawText();
                }
                catch (Exception e)
                {
                    Debug.LogError("[SpawnVehicleTestClient] Failed to read raw payload: " + e.Message);
                    return;
                }

                Debug.Log("[SpawnVehicleTestClient] Raw payload: " + json);

                SpawnVehicleEnvelope envelope;
                try
                {
                    envelope = JsonUtility.FromJson<SpawnVehicleEnvelope>(json);
                }
                catch (Exception e)
                {
                    Debug.LogError("[SpawnVehicleTestClient] Failed to parse payload: " + e.Message);
                    return;
                }

                if (envelope?.data == null)
                {
                    Debug.LogWarning("[SpawnVehicleTestClient] Parsed envelope has null data");
                    return;
                }

                Debug.Log(
                    $"[SpawnVehicleTestClient] event={envelope.@event} "
                    + $"trackId={envelope.data.trackId} type={envelope.data.type} "
                    + $"direction={envelope.data.direction} cameraId={envelope.data.cameraId} "
                    + $"timestamp={envelope.data.timestamp}"
                );
            });

            _socket.Connect();
        }

        private void OnDestroy()
        {
            _socket?.Disconnect();
        }
    }
}
