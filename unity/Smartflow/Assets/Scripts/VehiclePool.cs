using System.Collections.Generic;
using SmartFlow.Network;
using UnityEngine;

namespace SmartFlow.Vehicles
{
    public class VehiclePool : MonoBehaviour
    {
        private const int PoolSize = 120;

        [SerializeField] private GameObject _carPrefab;
        [SerializeField] private GameObject _truckPrefab;
        [SerializeField] private GameObject _motorcyclePrefab;

        // จุดอ้างอิงถนน: ลาก GameObject มาวาง/หมุน/สเกลในซีนเพื่อจัดตำแหน่งรถทั้งหมด
        // ตำแหน่งจากข้อมูล (x,z) จะถูกวาง "สัมพัทธ์" กับจุดนี้ (ถ้าเว้นว่าง = ใช้พิกัดโลกตรงๆ)
        [SerializeField] private Transform _originAnchor;

        // trackId → active controller
        private readonly Dictionary<string, VehicleController> _active = new(PoolSize);

        // type → dormant objects waiting to be reused
        private readonly Dictionary<string, Queue<VehicleController>> _dormant = new();

        private readonly List<string> _toRelease = new(PoolSize);

        private void Awake()
        {
            _dormant["car"] = new Queue<VehicleController>();
            _dormant["truck"] = new Queue<VehicleController>();
            _dormant["motorcycle"] = new Queue<VehicleController>();
        }

        public void ApplyFrame(List<VehicleData> vehicles)
        {
            var seenIds = new HashSet<string>(vehicles.Count);
            foreach (var v in vehicles)
                seenIds.Add(v.trackId);

            // Release absent vehicles first so their slots are available for new ones
            _toRelease.Clear();
            foreach (var id in _active.Keys)
                if (!seenIds.Contains(id))
                    _toRelease.Add(id);
            foreach (var id in _toRelease)
                Release(id);

            foreach (var v in vehicles)
            {
                var local = new Vector3(v.position.x, v.position.y, v.position.z);
                // ถ้ามี anchor: วางตำแหน่งสัมพัทธ์กับจุดอ้างอิง (ย้าย/หมุน/สเกลได้ในซีน)
                var pos = _originAnchor != null ? _originAnchor.TransformPoint(local) : local;

                if (_active.TryGetValue(v.trackId, out var ctrl))
                {
                    ctrl.UpdateTarget(pos);
                }
                else
                {
                    var newCtrl = Acquire(v.trackId, v.type, pos);
                    if (newCtrl != null)
                        _active[v.trackId] = newCtrl;
                    else
                        Debug.LogWarning($"[VehiclePool] Pool exhausted — could not spawn {v.trackId}");
                }
            }
        }

        private VehicleController Acquire(string trackId, string type, Vector3 position)
        {
            if (_active.Count >= PoolSize) return null;

            VehicleController ctrl;

            if (_dormant.TryGetValue(type, out var queue) && queue.Count > 0)
            {
                ctrl = queue.Dequeue();
            }
            else
            {
                var prefab = PrefabForType(type);
                if (prefab == null)
                {
                    Debug.LogError($"[VehiclePool] No prefab for vehicle type '{type}'");
                    return null;
                }
                var go = Instantiate(prefab, position, Quaternion.identity);
                ctrl = go.GetComponent<VehicleController>() ?? go.AddComponent<VehicleController>();
            }

            ctrl.gameObject.SetActive(true);
            ctrl.transform.position = position;
            ctrl.Init(trackId, type);
            return ctrl;
        }

        private void Release(string trackId)
        {
            if (!_active.TryGetValue(trackId, out var ctrl)) return;

            ctrl.gameObject.SetActive(false);
            _active.Remove(trackId);

            if (_dormant.TryGetValue(ctrl.VehicleType, out var queue))
                queue.Enqueue(ctrl);
        }

        private GameObject PrefabForType(string type) => type switch
        {
            "car" => _carPrefab,
            "truck" => _truckPrefab,
            "motorcycle" => _motorcyclePrefab,
            _ => null
        };
    }
}
