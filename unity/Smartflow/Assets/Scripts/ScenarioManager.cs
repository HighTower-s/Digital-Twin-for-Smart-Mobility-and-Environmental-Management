using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;

public class ScenarioManager : MonoBehaviour
{
    public static ScenarioManager Instance; 

    [System.Serializable]
    public class ScenarioConfig
    {
        public string scenarioName;
        public float minSpeed;
        public float maxSpeed;
        
        [Header("Lane Settings")]
        public float[] laneOffsets = { 0f }; 
    }

    [Header("UI References")]
    public TMP_Dropdown scenarioDropdown;
    public TMP_Text avgSpeedText;
    
    // UI สำหรับนับจำนวนรถ
    public TMP_Text inboundCountText;  
    public TMP_Text outboundCountText; 
    private int inboundTotalCount = 0;
    private int outboundTotalCount = 0;

    [Header("Vehicle Prefabs & Spawn")]
    public GameObject[] motorcyclePrefabs; 
    public GameObject[] carPrefabs;        
    
    [Header("Route Setup")]
    public WaypointRoute inboundRoute;   // เส้นทางขาเข้า
    public WaypointRoute outboundRoute;  // เส้นทางขาออก

    [Header("Scenario Configurations")]
    public ScenarioConfig[] scenarios;

    // 🟢 ระบบเข้าคิวป้องกันรถเกิดทับกัน (Queue System)
    private Queue<SmartFlow.Network.SpawnVehicleData> networkSpawnQueue = new Queue<SmartFlow.Network.SpawnVehicleData>();
    public float networkSpawnDelay = 0.5f; // หน่วงเวลา 0.5 วินาทีต่อคัน

    // ระบบ Object Pool
    private Dictionary<GameObject, Queue<GameObject>> vehiclePools = new Dictionary<GameObject, Queue<GameObject>>();
    private List<GameObject> activeVehicles = new List<GameObject>();

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        SetupDropdown();
        ChangeScenario(0);

        // 🟢 เริ่มระบบทยอยปล่อยรถจากคิว
        StartCoroutine(ProcessNetworkSpawnQueue());
    }

    void SetupDropdown()
    {
        scenarioDropdown.ClearOptions();
        List<string> options = new List<string>();
        foreach (var s in scenarios)
        {
            options.Add(s.scenarioName);
        }
        scenarioDropdown.AddOptions(options);
        scenarioDropdown.onValueChanged.AddListener(ChangeScenario);
    }

    public void ChangeScenario(int index)
    {
        ScenarioConfig selectedConfig = scenarios[index];
        float avgSpeed = (selectedConfig.minSpeed + selectedConfig.maxSpeed) / 2f;
        avgSpeedText.text = $"Avg Speed: {avgSpeed:F1} km/h";

        ClearOldVehicles();
    }

    private void UpdateVehicleCountUI()
    {
        if (inboundCountText != null) 
            inboundCountText.text = $"Inbound: {inboundTotalCount}";
        
        if (outboundCountText != null) 
            outboundCountText.text = $"Outbound: {outboundTotalCount}";
    }

    // ---------------------------------------------------
    // ส่วนของการรับ Event จาก Network (รับบัตรคิว)
    // ---------------------------------------------------
    public void SpawnVehicleFromNetwork(SmartFlow.Network.SpawnVehicleData netData)
    {
        // เมื่อมี Event มา ให้จับข้อมูลโยนเข้าคิวไว้ก่อน
        networkSpawnQueue.Enqueue(netData);
    }

    // ---------------------------------------------------
    // ส่วนของการทยอยสร้างรถ (เรียกคิว)
    // ---------------------------------------------------
    private IEnumerator ProcessNetworkSpawnQueue()
    {
        while (true) // ทำงานตลอดเวลา
        {
            // ถ้าในคิวมีรถรออยู่
            if (networkSpawnQueue.Count > 0)
            {
                // หยิบคิวแรกออกมา
                var netData = networkSpawnQueue.Dequeue();
                
                string dir = netData.direction.ToLower();
                WaypointRoute selectedRoute = null; 

                // เลือกเส้นทางและนับจำนวน
                if (dir == "in" || dir == "inbound")
                {
                    selectedRoute = inboundRoute;
                    inboundTotalCount++; 
                }
                else if (dir == "out" || dir == "outbound")
                {
                    selectedRoute = outboundRoute;
                    outboundTotalCount++; 
                }
                else
                {
                    Debug.LogWarning($"⚠️ ข้อมูล Direction ไม่ถูกต้อง: {netData.direction}");
                    continue; // ข้ามคิวนี้ไปเลย
                }

                if (selectedRoute == null || selectedRoute.waypoints.Count == 0) 
                {
                    Debug.LogWarning($"⚠️ ไม่พบ Waypoint สำหรับทิศทาง: {dir}");
                    continue; // ข้ามคิวนี้ไปเลย
                }

                // อัปเดต UI ทันที
                UpdateVehicleCountUI();

                // เลือก Prefab
                GameObject prefabToSpawn;
                if (netData.type.ToLower() == "motorcycle")
                {
                    prefabToSpawn = motorcyclePrefabs[Random.Range(0, motorcyclePrefabs.Length)];
                }
                else 
                {
                    prefabToSpawn = carPrefabs[Random.Range(0, carPrefabs.Length)];
                }

                // จัดการเรื่องเลน
                ScenarioConfig currentConfig = scenarios[scenarioDropdown.value];
                float randomLaneOffset = currentConfig.laneOffsets[Random.Range(0, currentConfig.laneOffsets.Length)];
                
                Transform startPoint = selectedRoute.waypoints[0];
                Vector3 finalSpawnPosition = startPoint.position + (startPoint.right * randomLaneOffset);

                // เบิกรถจาก Pool
                GameObject newVehicle = GetVehicleFromPool(prefabToSpawn);
                
                newVehicle.transform.position = finalSpawnPosition;
                newVehicle.transform.rotation = startPoint.rotation;
                
                VehicleMovement vehicleScript = newVehicle.GetComponent<VehicleMovement>();
                vehicleScript.targetSpeed = Random.Range(currentConfig.minSpeed, currentConfig.maxSpeed);
                vehicleScript.laneOffset = randomLaneOffset;
                vehicleScript.waypoints = selectedRoute.waypoints; 

                vehicleScript.ResetVehicle();
                
                Debug.Log($"🚗 Spawn รถสำเร็จ: {netData.type} ฝั่ง {netData.direction} (TrackID: {netData.trackId})");

                // 🟢 หน่วงเวลาก่อนจะดึงรถคิวถัดไปออกมา (ป้องกันรถทับกัน)
                yield return new WaitForSeconds(networkSpawnDelay);
            }
            else
            {
                // ถ้าไม่มีคิว ให้รอเฟรมถัดไป
                yield return null; 
            }
        }
    }

    // ---------------------------------------------------
    // ส่วนของ Object Pooling (โกดังเก็บรถ)
    // ---------------------------------------------------
    public GameObject GetVehicleFromPool(GameObject prefab)
    {
        if (!vehiclePools.ContainsKey(prefab))
        {
            vehiclePools[prefab] = new Queue<GameObject>();
        }

        GameObject vehicle;
        if (vehiclePools[prefab].Count > 0)
        {
            vehicle = vehiclePools[prefab].Dequeue();
            vehicle.SetActive(true); 
        }
        else 
        {
            vehicle = Instantiate(prefab); 
            vehicle.AddComponent<PoolMember>().originalPrefab = prefab; 
        }

        activeVehicles.Add(vehicle);
        return vehicle;
    }

    public void ReturnVehicleToPool(GameObject vehicle)
    {
        if (!vehicle.activeInHierarchy) return;

        vehicle.SetActive(false); 
        activeVehicles.Remove(vehicle);

        GameObject originalPrefab = vehicle.GetComponent<PoolMember>().originalPrefab;
        vehiclePools[originalPrefab].Enqueue(vehicle); 
    }

    void ClearOldVehicles()
    {
        for (int i = activeVehicles.Count - 1; i >= 0; i--)
        {
            ReturnVehicleToPool(activeVehicles[i]);
        }
    }
}

// คลาสเสริม เอาไว้แปะที่ตัวรถเพื่อจดจำว่ารถคันนี้สร้างมาจาก Prefab ตัวไหน
public class PoolMember : MonoBehaviour 
{ 
    public GameObject originalPrefab; 
}