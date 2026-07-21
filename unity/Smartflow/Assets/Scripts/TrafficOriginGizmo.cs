using UnityEngine;

namespace SmartFlow.CameraControl
{
    /// <summary>
    /// วาดกรอบถนน/เลน/จุดสปอน/ทิศทาง ในหน้า Scene ให้เห็นภาพ
    /// ใส่ที่ GameObject "TrafficOrigin" (empty)
    ///
    /// กฎเดียว: รถ "เกิดที่ object นี้" (จุดเขียว) แล้ววิ่งไปทาง +Z ของ object (ลูกศรน้ำเงิน) เสมอ
    /// - เปลี่ยนทิศรถ  = หมุน object นี้ (แกน Y)
    /// - เปลี่ยนจุดเกิด = ย้าย object นี้
    /// ตั้ง lanes / laneHalfWidth / roadLen ให้ "ตรงกับ .env" (LANES, LANE_HALF_WIDTH, ROAD_LEN)
    ///
    /// เขียว = จุดเกิด (รถเข้า) · แดง = ปลายถนน · เหลือง = ขอบถนน · ลูกศรฟ้า = ทิศวิ่ง
    /// </summary>
    [ExecuteAlways]
    public class TrafficOriginGizmo : MonoBehaviour
    {
        [Tooltip("ตำแหน่ง x กลางเลน (ต้องตรงกับ LANES ใน .env เป๊ะ) เช่น [-3.5, 0, 3.5] = 3 เลน")]
        public float[] lanes = { -3.5f, 0f, 3.5f };

        [Tooltip("ครึ่งความกว้างเลน (ต้องตรงกับ LANE_HALF_WIDTH ใน .env)")]
        public float laneHalfWidth = 1.6f;

        [Tooltip("ความยาวถนน (ROAD_LEN) — รถวิ่งจาก 0 ไป +Z เท่านี้แล้ววนกลับ")]
        public float roadLen = 200f;

        private void OnDrawGizmos()
        {
            if (lanes == null || lanes.Length == 0) return;

            // วาดในพิกัด local ของ object (ตาม position/rotation/scale) — z=0 คือจุดเกิด, +z คือทิศวิ่ง
            Gizmos.matrix = transform.localToWorldMatrix;

            float minX = float.MaxValue, maxX = float.MinValue;
            foreach (var lx in lanes)
            {
                minX = Mathf.Min(minX, lx - laneHalfWidth);
                maxX = Mathf.Max(maxX, lx + laneHalfWidth);
            }

            // ขอบถนน (เหลือง)
            Gizmos.color = new Color(1f, 0.85f, 0.2f, 0.9f);
            Line(minX, 0f, minX, roadLen);
            Line(maxX, 0f, maxX, roadLen);

            // เส้นแบ่งเลน (ขาวจาง)
            Gizmos.color = new Color(1f, 1f, 1f, 0.35f);
            foreach (var lx in lanes) Line(lx, 0f, lx, roadLen);

            // เส้นเกิด (เขียว) ที่ z=0 และปลายถนน (แดง) ที่ z=roadLen
            Gizmos.color = new Color(0.3f, 0.9f, 0.4f, 1f);
            Line(minX, 0f, maxX, 0f);
            foreach (var lx in lanes) Gizmos.DrawSphere(new Vector3(lx, 0f, 0f), 0.6f);
            Gizmos.color = new Color(1f, 0.3f, 0.3f, 1f);
            Line(minX, roadLen, maxX, roadLen);

            // ลูกศรทิศวิ่ง (กลางถนน ชี้ +z)
            float midX = (minX + maxX) * 0.5f;
            float headZ = roadLen * 0.35f;
            Gizmos.color = new Color(0.3f, 0.7f, 1f, 1f);
            Line(midX, 0f, midX, headZ);
            Line(midX, headZ, midX - 0.8f, headZ - 1.6f);
            Line(midX, headZ, midX + 0.8f, headZ - 1.6f);
        }

        private static void Line(float x1, float z1, float x2, float z2)
        {
            Gizmos.DrawLine(new Vector3(x1, 0f, z1), new Vector3(x2, 0f, z2));
        }
    }
}
