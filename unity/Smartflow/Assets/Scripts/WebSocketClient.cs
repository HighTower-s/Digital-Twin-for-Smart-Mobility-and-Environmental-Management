using System;
using SocketIOClient;
using SmartFlow.Vehicles;
using UnityEngine;

namespace SmartFlow.Network
{
    public class WebSocketClient : MonoBehaviour
    {
        [SerializeField] private string _serverUrl = "http://localhost:3000";
        [SerializeField] private VehiclePool _vehiclePool;

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
                Debug.Log("[WebSocketClient] Connected to " + _serverUrl);

            _socket.OnDisconnected += (_, reason) =>
                Debug.LogWarning("[WebSocketClient] Disconnected: " + reason);

            _socket.OnError += (_, error) =>
                Debug.LogError("[WebSocketClient] Error: " + error);

            _socket.OnUnityThread("frame", response =>
            {
                // GetValue<T>() uses System.Text.Json which skips public fields.
                // Extract raw JSON and use JsonUtility which handles [Serializable] fields.
                string json;
                try
                {
                    json = response.GetValue<System.Text.Json.JsonElement>().GetRawText();
                }
                catch (Exception e)
                {
                    Debug.LogError("[WebSocketClient] Failed to read raw frame: " + e.Message);
                    return;
                }

                FrameData frame;
                try
                {
                    frame = JsonUtility.FromJson<FrameData>(json);
                }
                catch (Exception e)
                {
                    Debug.LogError("[WebSocketClient] Failed to parse frame JSON: " + e.Message);
                    return;
                }

                if (frame?.vehicles == null)
                {
                    Debug.LogWarning("[WebSocketClient] Received frame with null vehicles array");
                    return;
                }

                // OnUnityThread ensures Unity API calls (Instantiate, SetActive, etc.) are safe
                _vehiclePool.ApplyFrame(frame.vehicles);
            });

            _socket.Connect();
        }

        private void OnDestroy()
        {
            _socket?.Disconnect();
        }
    }
}
