import { createServer } from 'http';
import { Server as SocketServer } from 'socket.io';
import { createApp } from './app';
import { PORT } from './config/env';
import { createApiRouter } from './routes/api';
import { registerUnityHandler } from './sockets/unityHandler';

const app = createApp();
const httpServer = createServer(app);
const io = new SocketServer(httpServer, {
  cors: { origin: '*' },
});

app.use(createApiRouter(io));
registerUnityHandler(io);

httpServer.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
