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

    // 🟢 ตัวแปรนับแยกประเภทรถทั้ง 4 แบบ (ขาเข้า)
    private int inboundCarCount = 0;
    private int inboundMotoCount = 0;
    private int inboundTruckCount = 0;
    private int inboundBusCount = 0;

    // 🟢 ตัวแปรนับแยกประเภทรถทั้ง 4 แบบ (ขาออก)
    private int outboundCarCount = 0;
    private int outboundMotoCount = 0;
    private int outboundTruckCount = 0;
    private int outboundBusCount = 0;

    [Header("Vehicle Prefabs & Spawn")]
    // 🟢 เพิ่มกล่องใส่ Prefab สำหรับรถ 4 ประเภท
    public GameObject[] motorcyclePrefabs;
    public GameObject[] carPrefabs;
    public GameObject[] truckPrefabs;
    public GameObject[] busPrefabs;

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

    // 🟢 อัปเดต UI ให้แสดงผลแยกประเภท 4 แบบ
    private void UpdateVehicleCountUI()
    {
        if (inboundCountText != null)
        {
            int totalIn = inboundCarCount + inboundMotoCount + inboundTruckCount + inboundBusCount;
            // ใช้ \n เพื่อขึ้นบรรทัดใหม่ จะได้ไม่ล้นขอบจอ
            inboundCountText.text = $"Inbound: {totalIn}\n(Car:{inboundCarCount} Moto:{inboundMotoCount} Truck:{inboundTruckCount} Bus:{inboundBusCount})";
        }

        if (outboundCountText != null)
        {
            int totalOut = outboundCarCount + outboundMotoCount + outboundTruckCount + outboundBusCount;
            outboundCountText.text = $"Outbound: {totalOut}\n(Car:{outboundCarCount} Moto:{outboundMotoCount} Truck:{outboundTruckCount} Bus:{outboundBusCount})";
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
                string vType = netData.type.ToLower();

                WaypointRoute selectedRoute = null;

                // 1. เช็กทิศทางวิ่ง
                if (dir == "in" || dir == "inbound") selectedRoute = inboundRoute;
                else if (dir == "out" || dir == "outbound") selectedRoute = outboundRoute;
                else
                {
                    Debug.LogWarning($"⚠️ ข้อมูล Direction ไม่ถูกต้อง: {netData.direction}");
                    continue;
                }

                if (selectedRoute == null || selectedRoute.waypoints.Count == 0) continue;

                // 2. 🟢 จัดการการนับเลข และเลือกกลุ่ม Prefab ให้ตรงตาม Type
                GameObject[] selectedPrefabArray = null;

                if (vType == "motorcycle" || vType == "moto")
                {
                    selectedPrefabArray = motorcyclePrefabs;
                    if (selectedRoute == inboundRoute) inboundMotoCount++; else outboundMotoCount++;
                }
                else if (vType == "truck")
                {
                    selectedPrefabArray = truckPrefabs;
                    if (selectedRoute == inboundRoute) inboundTruckCount++; else outboundTruckCount++;
                }
                else if (vType == "bus")
                {
                    selectedPrefabArray = busPrefabs;
                    if (selectedRoute == inboundRoute) inboundBusCount++; else outboundBusCount++;
                }
                else
                {
                    // กรณีเป็น "car" หรือคำแปลกๆ ที่ไม่รู้จัก จะปัดตกเป็นรถยนต์ทั้งหมด
                    selectedPrefabArray = carPrefabs;
                    if (selectedRoute == inboundRoute) inboundCarCount++; else outboundCarCount++;
                }

                // อัปเดต UI ทันที
                UpdateVehicleCountUI();

                // ป้องกัน Error ถ้าใน Unity ไม่ได้ลาก Prefab มาใส่ใน Array
                if (selectedPrefabArray == null || selectedPrefabArray.Length == 0)
                {
                    Debug.LogWarning($"⚠️ ไม่มี Prefab สำหรับรถประเภท: {vType} กรุณาใส่ Prefab ใน Inspector");
                    continue; // ข้ามการสร้างรถคันนี้ไปเลยถ้าไม่มีโมเดล
                }

                // 3. สุ่มเลือกรถ 1 คัน จาก Array ที่เราเลือกไว้
                GameObject prefabToSpawn = selectedPrefabArray[Random.Range(0, selectedPrefabArray.Length)];

                // จัดการเลน
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