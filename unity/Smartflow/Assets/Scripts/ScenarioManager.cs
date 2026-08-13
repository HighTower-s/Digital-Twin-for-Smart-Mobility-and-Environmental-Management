using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;

public class ScenarioManager : MonoBehaviour
{
    public static ScenarioManager Instance; // ทำเป็น Singleton เพื่อให้รถเรียกใช้ได้ง่าย

//[System.Serializable]
//    public class TrafficFlow
//    {
//        public string direction; // ค่าจะเป็น "inbound" หรือ "outbound"
//        public int motorcycleCount;
//        public int carCount;
//    }

//    [System.Serializable]
//    public class VehicleData
//    {
//        public TrafficFlow[] flows; // เก็บข้อมูลเป็นลิตส์ของแต่ละทิศทาง
//    }

    [System.Serializable]
    public class ScenarioConfig
    {
        // ข้อมูลส่วนนี้ตั้งค่าใน Unity Inspector (ควบคุมพฤติกรรม)
        public string scenarioName;
        public float minSpeed;
        public float maxSpeed;
        
        [Header("Lane Settings")]
        [Tooltip("ใส่ระยะห่างแกน X ของแต่ละเลน เช่น [0] คือ 1 เลน, [-3, 0, 3] คือ 3 เลน")]
        public float[] laneOffsets = { 0f }; 
    }

    [Header("UI References")]
    public TMP_Dropdown scenarioDropdown;
    public TMP_Text avgSpeedText;

    [Header("Vehicle Prefabs & Spawn")]
    public GameObject[] motorcyclePrefabs; 
    public GameObject[] carPrefabs;        
    
    public float spawnDelay = 1f;


    [Header("Route Setup (ขาเข้า / ขาออก)")]
    public WaypointRoute inboundRoute;   // เส้นทางขาเข้า
    public WaypointRoute outboundRoute;  // เส้นทางขาออก

    // เปลี่ยน Mockup JSON ให้เป็นแบบใหม่
    //private string mockJsonData = "{\"flows\": [{\"direction\": \"inbound\", \"motorcycleCount\": 2, \"carCount\": 15}, {\"direction\": \"outbound\", \"motorcycleCount\": 2, \"carCount\": 15}]}";


    // เก็บข้อมูลว่ารถคันที่จะ Spawn ต้องเป็นประเภทไหน และวิ่งฝั่งไหน
    //public class SpawnTicket
    //{
    //    public bool isMotorcycle;
    //    public WaypointRoute route;
    //}

    private Queue<string> recentTrackIds = new Queue<string>();

    [Header("Scenario Configurations")]
    public ScenarioConfig[] scenarios;

    // ข้อมูล JSON จำลอง (เก็บแค่จำนวนรถ)
    //private VehicleData vehicleCounts; // ตัวแปรเก็บจำนวนรถที่อ่านจาก JSON

    //private Coroutine spawnCoroutine;

    // --- ระบบ Object Pool ---
    private Dictionary<GameObject, Queue<GameObject>> vehiclePools = new Dictionary<GameObject, Queue<GameObject>>();
    
    // ลิสต์รถที่กำลังวิ่งอยู่บนถนน (ประกาศแค่รอบเดียวพอครับ)
    private List<GameObject> activeVehicles = new List<GameObject>();

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        // 1. อ่านข้อมูลจำนวนรถจาก JSON
        //vehicleCounts = JsonUtility.FromJson<VehicleData>(mockJsonData);

        // 2. ตั้งค่า UI Dropdown
        SetupDropdown();

        // 3. เริ่มรัน Scenario แรก
        ChangeScenario(0);
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

        // อัปเดต UI บอกความเร็วเฉลี่ย
        float avgSpeed = (selectedConfig.minSpeed + selectedConfig.maxSpeed) / 2f;
        avgSpeedText.text = $"Avg Speed: {avgSpeed:F1} km/h";

        // ล้างรถชุดเก่า (ส่งคืน Pool)
        ClearOldVehicles();

        //if (spawnCoroutine != null) StopCoroutine(spawnCoroutine);
        
        // เริ่มสร้างรถชุดใหม่
        //spawnCoroutine = StartCoroutine(SpawnVehiclesRoutine(selectedConfig));
    }

    // ---------------------------------------------------
    // 🟢 ส่วนของ Object Pooling (เบิก/คืน รถ) 🟢
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
            vehicle.SetActive(true); // เปิดใช้งานรถเก่า
        }
        else 
        {
            vehicle = Instantiate(prefab); // สร้างใหม่ถ้าโกดังว่าง
            vehicle.AddComponent<PoolMember>().originalPrefab = prefab; // ติดป้ายบอกรุ่น
        }

        activeVehicles.Add(vehicle);
        return vehicle;
    }

    public void ReturnVehicleToPool(GameObject vehicle)
    {
        if (!vehicle.activeInHierarchy) return;

        vehicle.SetActive(false); // ซ่อนรถ
        activeVehicles.Remove(vehicle);

        GameObject originalPrefab = vehicle.GetComponent<PoolMember>().originalPrefab;
        vehiclePools[originalPrefab].Enqueue(vehicle); // เก็บเข้าโกดัง
    }

    void ClearOldVehicles()
    {
        // คืนรถทุกคันเข้า Pool แทนการใช้ Destroy
        for (int i = activeVehicles.Count - 1; i >= 0; i--)
        {
            ReturnVehicleToPool(activeVehicles[i]);
        }
    }

    // ---------------------------------------------------
    // 🟢 ส่วนของการ Spawn รถ 🟢
    // ---------------------------------------------------

    // IEnumerator SpawnVehiclesRoutine(ScenarioConfig config)
    // {
    //     // 1. สร้างกล่องเปล่าเพื่อเก็บตั๋วรถทุกคัน
    //     List<SpawnTicket> spawnBox = new List<SpawnTicket>();

    //     // 2. อ่านข้อมูลจาก JSON แล้วสร้างตั๋วใส่ลงกล่อง
    //     foreach (TrafficFlow flow in vehicleCounts.flows)
    //     {
    //         WaypointRoute selectedRoute = (flow.direction.ToLower() == "inbound") ? inboundRoute : outboundRoute;

    //         // ใส่ตั๋วมอเตอร์ไซค์
    //         for (int i = 0; i < flow.motorcycleCount; i++)
    //         {
    //             spawnBox.Add(new SpawnTicket { isMotorcycle = true, route = selectedRoute });
    //         }

    //         // ใส่ตั๋วรถยนต์
    //         for (int i = 0; i < flow.carCount; i++)
    //         {
    //             spawnBox.Add(new SpawnTicket { isMotorcycle = false, route = selectedRoute });
    //         }
    //     }

    //     // 3. เริ่มหยิบตั๋วออกจากกล่องแบบสุ่มทีละใบ จนกว่ากล่องจะว่างเปล่า
    //     while (spawnBox.Count > 0)
    //     {
    //         // สุ่มล้วงตั๋วขึ้นมา 1 ใบ
    //         int randomIndex = Random.Range(0, spawnBox.Count);
    //         SpawnTicket ticket = spawnBox[randomIndex];

    //         // 4. เตรียม Prefab และเรียกใช้งาน
    //         GameObject prefabToSpawn;
    //         if (ticket.isMotorcycle)
    //         {
    //             int randomMotoModel = Random.Range(0, motorcyclePrefabs.Length);
    //             prefabToSpawn = motorcyclePrefabs[randomMotoModel];
    //         }
    //         else
    //         {
    //             int randomCarModel = Random.Range(0, carPrefabs.Length);
    //             prefabToSpawn = carPrefabs[randomCarModel];
    //         }

    //         // สั่ง Spawn รถ
    //         SpawnSingleVehicle(prefabToSpawn, config, ticket.route);

    //         // 5. หยิบตั๋วใบนี้ทิ้งไป จะได้ไม่ซ้ำ
    //         spawnBox.RemoveAt(randomIndex);

    //         // รอเวลาหน่วงก่อนหยิบตั๋วใบถัดไป
    //         yield return new WaitForSeconds(spawnDelay);
    //     }
    // }

    // 🟢 อัปเดตฟังก์ชันนี้ ให้รับค่า selectedRoute เข้ามาด้วย
    void SpawnSingleVehicle(GameObject prefab, ScenarioConfig config, WaypointRoute routePath)
    {
        if (routePath == null || routePath.waypoints.Count == 0) return;

        float randomLaneOffset = config.laneOffsets[Random.Range(0, config.laneOffsets.Length)];
        Transform startPoint = routePath.waypoints[0];
        
        // จุดเกิด (Spawn) จะคำนวณจาก Waypoint จุดแรกของเส้นทางที่ถูกส่งเข้ามา
        Vector3 finalSpawnPosition = startPoint.position + (startPoint.right * randomLaneOffset);

        GameObject newVehicle = GetVehicleFromPool(prefab);
        
        newVehicle.transform.position = finalSpawnPosition;
        newVehicle.transform.rotation = startPoint.rotation;
        
        VehicleMovement vehicleScript = newVehicle.GetComponent<VehicleMovement>();
        vehicleScript.targetSpeed = Random.Range(config.minSpeed, config.maxSpeed);
        vehicleScript.laneOffset = randomLaneOffset;
        
        // 🟢 ส่งจุด Waypoint ของเส้นทางฝั่งนั้นๆ ไปให้รถ
        vehicleScript.waypoints = routePath.waypoints; 

        vehicleScript.ResetVehicle();
    }
    // เพิ่มฟังก์ชันนี้ไว้ใน ScenarioManager.cs
    public void SpawnVehicleFromNetwork(SmartFlow.Network.SpawnVehicleData netData)
    {
        // 1. นำ direction มาแปลงเป็นตัวพิมพ์เล็กก่อนเพื่อความชัวร์
        string dir = netData.direction.ToLower();
        
        WaypointRoute selectedRoute;

        // 2. เช็กเงื่อนไข (รองรับทั้ง "in" และ "inbound")
        if (dir == "in" || dir == "inbound")
        {
            selectedRoute = inboundRoute;
        }
        else if (dir == "out" || dir == "outbound")
        {
            selectedRoute = outboundRoute;
        }
        else
        {
            // ถ้าส่งค่าแปลกๆ มา ให้แจ้งเตือนและยกเลิกการสร้างรถ
            Debug.LogWarning($"⚠️ ข้อมูล Direction ไม่ถูกต้อง: {netData.direction}");
            return; 
        }

        if (selectedRoute == null || selectedRoute.waypoints.Count == 0) 
        {
            Debug.LogWarning($"⚠️ ไม่พบ Waypoint สำหรับทิศทาง: {dir}");
            return;
        }
        // --- 🟢 ระบบป้องกันรถซ้ำ ---
        if (recentTrackIds.Contains(netData.trackId))
        {
            Debug.Log($"🛑 ปฏิเสธการสร้างรถ: TrackID {netData.trackId} ถูกสร้างไปแล้ว");
            return; // หยุดการทำงาน ไม่สร้างรถซ้ำ
        }

        // จดจำ TrackID นี้ไว้
        recentTrackIds.Enqueue(netData.trackId);
        // ถ้าคิวเกิน 100 คัน ให้ลบอันเก่าสุดทิ้ง (ป้องกันกิน Memory)
        if (recentTrackIds.Count > 100) recentTrackIds.Dequeue();
        // ---------------------------
        // 1. เลือกเส้นทาง (Inbound หรือ Outbound)
        WaypointRoute selectedRoute = (netData.direction.ToLower() == "inbound") ? inboundRoute : outboundRoute;
        
        if (selectedRoute == null || selectedRoute.waypoints.Count == 0) 
        {
            Debug.LogWarning($"ไม่พบเส้นทางสำหรับ direction: {netData.direction}");
            return;
        }

        // 2. เลือกรถจาก Pool ตาม Type (motorcycle หรือ car)
        GameObject prefabToSpawn;
        if (netData.type.ToLower() == "motorcycle")
        {
            prefabToSpawn = motorcyclePrefabs[Random.Range(0, motorcyclePrefabs.Length)];
        }
        else 
        {
            // ถ้าเป็น car หรือประเภทอื่นๆ ให้ใช้ Prefab รถยนต์
            prefabToSpawn = carPrefabs[Random.Range(0, carPrefabs.Length)];
        }

        // 3. ดึง Config ปัจจุบัน (เพื่อให้รู้ว่าจะให้รถวิ่งเร็วแค่ไหน เลนไหน)
        // สมมติว่าตอนนี้เราดึงจาก Scenario ที่เลือกอยู่ (index ตาม Dropdown)
        ScenarioConfig currentConfig = scenarios[scenarioDropdown.value];

        // 4. สุ่มเลน
        float randomLaneOffset = currentConfig.laneOffsets[Random.Range(0, currentConfig.laneOffsets.Length)];
        Transform startPoint = selectedRoute.waypoints[0];
        Vector3 finalSpawnPosition = startPoint.position + (startPoint.right * randomLaneOffset);

        // 5. เบิกรถจาก Pool
        GameObject newVehicle = GetVehicleFromPool(prefabToSpawn);
        
        // 6. ตั้งค่าตำแหน่งและส่งข้อมูลให้รถ
        newVehicle.transform.position = finalSpawnPosition;
        newVehicle.transform.rotation = startPoint.rotation;
        
        VehicleMovement vehicleScript = newVehicle.GetComponent<VehicleMovement>();
        vehicleScript.targetSpeed = Random.Range(currentConfig.minSpeed, currentConfig.maxSpeed);
        vehicleScript.laneOffset = randomLaneOffset;
        vehicleScript.waypoints = selectedRoute.waypoints; 

        vehicleScript.ResetVehicle();
        
        Debug.Log($"🚗 Spawn รถสำเร็จ: {netData.type} ฝั่ง {netData.direction} (TrackID: {netData.trackId})");
    }
}

// คลาสเสริม เอาไว้แปะที่ตัวรถเพื่อจดจำว่ารถคันนี้สร้างมาจาก Prefab ตัวไหน
public class PoolMember : MonoBehaviour 
{ 
    public GameObject originalPrefab; 
}