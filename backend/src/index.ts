import 'dotenv/config';
import express from 'express';
import { createServer } from 'http';
import path from 'path';
import { Server as SocketServer } from 'socket.io';
import { PORT } from './constants';
import { createIngestRouter } from './routes/ingest';
import healthRouter from './routes/health';

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const httpServer = createServer(app);
const io = new SocketServer(httpServer, {
  cors: { origin: '*' },
});

app.use(healthRouter);
app.use(createIngestRouter(io));

io.on('connection', (socket) => {
  console.log(`[ws] client connected: ${socket.id}`);
  socket.on('disconnect', () => {
    console.log(`[ws] client disconnected: ${socket.id}`);
  });
});

httpServer.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
