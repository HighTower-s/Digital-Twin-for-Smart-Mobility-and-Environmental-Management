using UnityEngine;

namespace SmartFlow.Vehicles
{
    public class VehicleController : MonoBehaviour
    {
        private const float LerpDuration = 1.0f;

        public string TrackId { get; private set; }
        public string VehicleType { get; private set; }

        private Vector3 _startPosition;
        private Vector3 _targetPosition;
        private float _lerpTimer;

        public void Init(string trackId, string vehicleType)
        {
            TrackId = trackId;
            VehicleType = vehicleType;
            _startPosition = transform.position;
            _targetPosition = transform.position;
            _lerpTimer = LerpDuration;
        }

        public void UpdateTarget(Vector3 newPosition)
        {
            _startPosition = transform.position;
            _targetPosition = newPosition;
            _lerpTimer = 0f;
        }

        private void Update()
        {
            if (_lerpTimer >= LerpDuration) return;

            _lerpTimer += Time.deltaTime;
            float t = Mathf.Clamp01(_lerpTimer / LerpDuration);
            transform.position = Vector3.Lerp(_startPosition, _targetPosition, t);
        }
    }
}
