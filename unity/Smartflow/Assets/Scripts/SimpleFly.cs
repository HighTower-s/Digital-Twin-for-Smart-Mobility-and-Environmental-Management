using UnityEngine;

public class SimpleFly : MonoBehaviour
{
    public float flySpeed = 10f; // ความเร็วในการบิน (ปรับได้ใน Inspector)

    void Update()
    {
        // 1. รับค่าการกดปุ่ม W, S (แกน Z) และ A, D (แกน X)
        float x = Input.GetAxis("Horizontal");
        float z = Input.GetAxis("Vertical");
        float y = 0f;

        // 2. รับค่าการกดปุ่มสำหรับบินขึ้น-ลง (แกน Y)
        if (Input.GetKey(KeyCode.Space)) 
        {
            y = 1f; // บินขึ้น
        }
        else if (Input.GetKey(KeyCode.LeftShift)) 
        {
            y = -1f; // บินลง
        }

        // 3. รวมทิศทางทั้งหมด
        Vector3 moveDirection = new Vector3(x, y, z);

        // 4. สั่งให้ Player ขยับไปตามทิศทาง (อ้างอิงจากหน้าของ Player)
        transform.Translate(moveDirection * flySpeed * Time.deltaTime);
    }
}