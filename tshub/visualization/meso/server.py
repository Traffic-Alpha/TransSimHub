'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 中观大屏的本地服务 (只依赖标准库, 不引入 flask/fastapi)
- 后台线程跑 ThreadingHTTPServer, 仿真主循环调用 push() 推送每一帧;
- 浏览器通过 SSE (/stream) 接收, 不需要轮询;
- push() 永不阻塞: 每个浏览器一个有界队列, 满了就丢最旧的一帧。
  仿真的速度不能被浏览器的消费速度拖慢, 大屏掉几帧比仿真卡住要好。
@LastEditTime: 2026-08-11 10:00:00
'''
import json
import queue
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional

from loguru import logger

WEB_DIR = Path(__file__).parent / 'web'
_CONTENT_TYPES = {'.html': 'text/html; charset=utf-8',
                  '.js': 'application/javascript; charset=utf-8',
                  '.css': 'text/css; charset=utf-8'}


class DashboardServer:
    """中观大屏的服务端.

    典型用法 (与 env 解耦, 由使用者在自己的循环里推送):
        dashboard = DashboardServer(port=8910)
        dashboard.start()
        dashboard.set_static(build_static_payload(obs))
        while not done:
            obs, ... = env.step(actions)
            dashboard.push(build_frame_payload(...))
        dashboard.stop()
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 8910,
                 client_queue_size: int = 8) -> None:
        self.host = host
        self.port = port
        self.client_queue_size = client_queue_size

        self._static_payload: Dict[str, Any] = {}
        self._latest_frame: Optional[Dict[str, Any]] = None  # 新连上的浏览器先补一帧
        self._client_queues: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # ---------------- 对外接口 ---------------- #
    def start(self) -> str:
        """起后台线程, 返回大屏的 URL"""
        handler = _make_handler(self)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.daemon_threads = True  # 进程退出时不被 SSE 长连接卡住
        self.port = self._httpd.server_address[1]  # port=0 时取实际分配的端口
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        url = f'http://{self.host}:{self.port}'
        logger.info(f'SIM: 中观大屏已启动, 打开 {url} 查看.')
        return url

    def set_static(self, payload: Dict[str, Any]) -> None:
        """设置静态数据 (路网几何等), 在 reset 之后调用一次"""
        with self._lock:
            self._static_payload = payload

    def push(self, frame: Dict[str, Any]) -> None:
        """推送一帧. 非阻塞: 队列满时丢弃该客户端最旧的一帧"""
        with self._lock:
            self._latest_frame = frame
            client_queues = list(self._client_queues)
        for client_queue in client_queues:
            try:
                client_queue.put_nowait(frame)
            except queue.Full:
                try:
                    client_queue.get_nowait()  # 丢掉最旧的一帧, 给新帧腾位置
                    client_queue.put_nowait(frame)
                except (queue.Empty, queue.Full):
                    pass

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
            logger.info('SIM: 中观大屏已关闭.')

    # ---------------- 内部: 客户端管理 ---------------- #
    def _register_client(self) -> queue.Queue:
        client_queue = queue.Queue(maxsize=self.client_queue_size)
        with self._lock:
            self._client_queues.append(client_queue)
            latest_frame = self._latest_frame
        if latest_frame is not None:
            client_queue.put_nowait(latest_frame)  # 新连上的浏览器立刻有画面
        return client_queue

    def _unregister_client(self, client_queue: queue.Queue) -> None:
        with self._lock:
            if client_queue in self._client_queues:
                self._client_queues.remove(client_queue)

    def _get_static(self) -> Dict[str, Any]:
        with self._lock:
            return self._static_payload


def _make_handler(dashboard: DashboardServer):
    class DashboardHandler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, format, *args):
            pass  # 静音: 每帧一条 HTTP 日志会淹没仿真日志

        def do_GET(self):
            if self.path.startswith('/stream'):
                self._serve_stream()
            elif self.path.startswith('/static.json'):
                self._serve_json(dashboard._get_static())
            else:
                self._serve_file()

        # -- 路由实现 -- #
        def _serve_file(self):
            name = 'index.html' if self.path in ('/', '') else self.path.lstrip('/').split('?')[0]
            file_path = (WEB_DIR / name).resolve()
            if (WEB_DIR.resolve() not in file_path.parents) or (not file_path.is_file()):
                self.send_error(404)
                return
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', _CONTENT_TYPES.get(file_path.suffix, 'application/octet-stream'))
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_json(self, payload):
            body = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_stream(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            client_queue = dashboard._register_client()
            try:
                while True:
                    try:
                        frame = client_queue.get(timeout=10)
                    except queue.Empty:
                        self.wfile.write(b': keep-alive\n\n')  # 心跳, 防代理断开
                        self.wfile.flush()
                        continue
                    payload = json.dumps(frame).encode('utf-8')
                    self.wfile.write(b'data: ' + payload + b'\n\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # 浏览器关掉了, 正常情况
            finally:
                dashboard._unregister_client(client_queue)

    return DashboardHandler
