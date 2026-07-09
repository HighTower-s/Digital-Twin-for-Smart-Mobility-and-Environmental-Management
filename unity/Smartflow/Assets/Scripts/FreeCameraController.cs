using UnityEngine;
using UnityEngine.InputSystem;   // ใช้ Input System แบบใหม่ (ไม่ต้องแก้ Active Input Handling)

namespace SmartFlow.CameraControl
{
    /// <summary>
    /// กล้องบินอิสระตอน Play mode (เหมือน Scene view) — เขียนด้วย Input System แบบใหม่
    /// - คลิกขวาค้าง = หมุนมอง (mouse look)
    /// - W/A/S/D = เดินหน้า/ซ้าย/ถอย/ขวา · Q/E = ลง/ขึ้น (หรือ Space/Ctrl)
    /// - Shift = เร่งความเร็ว · ล้อเมาส์ = ปรับความเร็วฐาน
    /// ใส่สคริปต์นี้ที่ Main Camera
    /// ต้องมี package com.unity.inputsystem (โปรเจกต์นี้มีอยู่แล้ว)
    /// </summary>
    public class FreeCameraController : MonoBehaviour
    {
        [Header("Movement")]
        [SerializeField] private float _moveSpeed = 20f;
        [SerializeField] private float _boostMultiplier = 4f;   // กด Shift
        [SerializeField] private float _minSpeed = 2f;
        [SerializeField] private float _maxSpeed = 200f;

        [Header("Look")]
        [SerializeField] private float _lookSensitivity = 0.1f;
        [SerializeField] private bool _requireRightMouseToLook = true;

        private float _yaw;
        private float _pitch;

        private void Start()
        {
            var e = transform.eulerAngles;
            _yaw = e.y;
            _pitch = e.x;
        }

        private void Update()
        {
            var kb = Keyboard.current;
            var mouse = Mouse.current;
            if (kb == null || mouse == null) return;   // ไม่มีอุปกรณ์ก็ข้าม

            HandleLook(mouse);
            HandleMove(kb);
            HandleSpeedScroll(mouse);
        }

        private void HandleLook(Mouse mouse)
        {
            if (_requireRightMouseToLook && !mouse.rightButton.isPressed)
                return;

            Vector2 delta = mouse.delta.ReadValue();
            _yaw += delta.x * _lookSensitivity;
            _pitch -= delta.y * _lookSensitivity;
            _pitch = Mathf.Clamp(_pitch, -89f, 89f);
            transform.rotation = Quaternion.Euler(_pitch, _yaw, 0f);
        }

        private void HandleMove(Keyboard kb)
        {
            float speed = _moveSpeed * (kb.leftShiftKey.isPressed ? _boostMultiplier : 1f);

            Vector3 dir = Vector3.zero;
            if (kb.wKey.isPressed) dir += transform.forward;
            if (kb.sKey.isPressed) dir -= transform.forward;
            if (kb.dKey.isPressed) dir += transform.right;
            if (kb.aKey.isPressed) dir -= transform.right;
            if (kb.eKey.isPressed || kb.spaceKey.isPressed) dir += Vector3.up;
            if (kb.qKey.isPressed || kb.leftCtrlKey.isPressed) dir -= Vector3.up;

            transform.position += dir.normalized * speed * Time.deltaTime;
        }

        private void HandleSpeedScroll(Mouse mouse)
        {
            float scroll = mouse.scroll.ReadValue().y;
            if (Mathf.Abs(scroll) > 0.01f)
                _moveSpeed = Mathf.Clamp(_moveSpeed + Mathf.Sign(scroll) * 4f, _minSpeed, _maxSpeed);
        }
    }
}
