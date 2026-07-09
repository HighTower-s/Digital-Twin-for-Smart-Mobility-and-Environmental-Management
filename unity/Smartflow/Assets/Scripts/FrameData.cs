using System;
using System.Collections.Generic;

namespace SmartFlow.Network
{
    [Serializable]
    public class FrameData
    {
        public string timestamp;
        public string cameraId;
        public int frameCount;
        public List<VehicleData> vehicles;
    }

    [Serializable]
    public class VehicleData
    {
        public string trackId;
        public string type;
        public float speed;
        public PositionData position;
    }

    [Serializable]
    public class PositionData
    {
        public float x;
        public float y;
        public float z;
    }
}
