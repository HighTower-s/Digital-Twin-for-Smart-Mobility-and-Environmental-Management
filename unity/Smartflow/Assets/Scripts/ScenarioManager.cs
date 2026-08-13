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
    
    // 🟢 เปลี่ยนมาใช้ตัวแปรนับแยกประเภทรถ
    private int inboundCarCount = 0;
    private int inboundMotoCount = 0;
    private int outboundCarCount = 0;
    private int outboundMotoCount = 0;

    [Header("Vehicle Prefabs & Spawn")]
    public GameObject[] motorcyclePrefabs; 
    public GameObject[] carPrefabs;        
    
    [Header("Route Setup")]
    public WaypointRoute inboundRoute;   
    public WaypointRoute outboundRoute;  

    [Header("Scenario Configurations")]
    public ScenarioConfig[] scenarios;

    // ระบบคิว
    private Queue<SmartFlow.Network.SpawnVehicleData> networkSpawnQueue = new Queue<SmartFlow.Network.SpawnVehicleData>();
    public float networkSpawnDelay = 0.5f; 

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

    // 🟢 อัปเดต UI ให้แสดงผลแยกประเภท
    private void UpdateVehicleCountUI()
    {
        if (inboundCountText != null) 
        {
            int totalIn = inboundCarCount + inboundMotoCount;
            inboundCountText.text = $"Inbound: {totalIn} (Car: {inboundCarCount}, Moto: {inboundMotoCount})";
        }
        
        if (outboundCountText != null) 
        {
            int totalOut = outboundCarCount + outboundMotoCount;
            outboundCountText.text = $"Outbound: {totalOut} (Car: {outboundCarCount}, Moto: {outboundMotoCount})";
        }
    }

    public void SpawnVehicleFromNetwork(SmartFlow.Network.SpawnVehicleData netData)
    {
        networkSpawnQueue.Enqueue(netData);
    }

    private IEnumerator ProcessNetworkSpawnQueue()
    {
        while (true)
        {
            if (networkSpawnQueue.Count > 0)
            {
                var netData = networkSpawnQueue.Dequeue();
                
                string dir = netData.direction.ToLower();
                string vType = netData.type.ToLower(); // 🟢 อ่านประเภทรถจาก Network
                
                WaypointRoute selectedRoute = null; 

                // 🟢 แยกเงื่อนไขการนับว่าวิ่งเลนไหน และเป็นรถประเภทไหน
                if (dir == "in" || dir == "inbound")
                {
                    selectedRoute = inboundRoute;
                    if (vType == "motorcycle" || vType == "moto") inboundMotoCount++;
                    else inboundCarCount++; // ถ้าไม่ใช่ระบุว่ามอเตอร์ไซค์ ให้นับเป็นรถยนต์ทั้งหมด
                }
                else if (dir == "out" || dir == "outbound")
                {
                    selectedRoute = outboundRoute;
                    if (vType == "motorcycle" || vType == "moto") outboundMotoCount++;
                    else outboundCarCount++;
                }
                else
                {
                    Debug.LogWarning($"⚠️ ข้อมูล Direction ไม่ถูกต้อง: {netData.direction}");
                    continue; 
                }

                if (selectedRoute == null || selectedRoute.waypoints.Count == 0) 
                {
                    Debug.LogWarning($"⚠️ ไม่พบ Waypoint สำหรับทิศทาง: {dir}");
                    continue; 
                }

                UpdateVehicleCountUI(); // 🟢 อัปเดตตัวเลขบนจอ

                // เลือกรถจาก Pool
                GameObject prefabToSpawn;
                if (vType == "motorcycle" || vType == "moto")
                {
                    prefabToSpawn = motorcyclePrefabs[Random.Range(0, motorcyclePrefabs.Length)];
                }
                else 
                {
                    prefabToSpawn = carPrefabs[Random.Range(0, carPrefabs.Length)];
                }

                // จัดการเลน
                ScenarioConfig currentConfig = scenarios[scenarioDropdown.value];
                float randomLaneOffset = currentConfig.laneOffsets[Random.Range(0, currentConfig.laneOffsets.Length)];
                
                Transform startPoint = selectedRoute.waypoints[0];
                Vector3 finalSpawnPosition = startPoint.position + (startPoint.right * randomLaneOffset);

                // เบิกรถ
                GameObject newVehicle = GetVehicleFromPool(prefabToSpawn);
                
                newVehicle.transform.position = finalSpawnPosition;
                newVehicle.transform.rotation = startPoint.rotation;
                
                VehicleMovement vehicleScript = newVehicle.GetComponent<VehicleMovement>();
                vehicleScript.targetSpeed = Random.Range(currentConfig.minSpeed, currentConfig.maxSpeed);
                vehicleScript.laneOffset = randomLaneOffset;
                vehicleScript.waypoints = selectedRoute.waypoints; 

                vehicleScript.ResetVehicle();
                
                Debug.Log($"🚗 Spawn รถสำเร็จ: {netData.type} ฝั่ง {netData.direction} (TrackID: {netData.trackId})");

                yield return new WaitForSeconds(networkSpawnDelay);
            }
            else
            {
                yield return null; 
            }
        }
    }

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

public class PoolMember : MonoBehaviour 
{ 
    public GameObject originalPrefab; 
}