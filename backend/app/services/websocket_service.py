"""
WebSocket服务 - 实时任务状态通知和实时通信
"""
import asyncio
import json
import logging
import time
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request

from app.services.task_queue import get_task_queue, TaskStatus

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.socketio: Optional[SocketIO] = None
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        self.task_subscribers: Dict[str, Set[str]] = {}  # task_id -> set of session_ids
        self.room_subscribers: Dict[str, Set[str]] = {}  # room_name -> set of session_ids
        self.client_heartbeats: Dict[str, datetime] = {}
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'messages_received': 0
        }
    
    def init_socketio(self, app):
        """初始化SocketIO"""
        try:
            self.socketio = SocketIO(
                app,
                cors_allowed_origins="*",
                logger=False,
                engineio_logger=False,
                async_mode='threading'
            )
            
            # 注册事件处理器
            self._register_handlers()
            
            # 启动心跳检查和状态监控
            self._start_background_tasks()
            
            logger.info("WebSocket manager initialized successfully")
            return self.socketio
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket manager: {str(e)}")
            raise
    
    def _register_handlers(self):
        """注册WebSocket事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接事件"""
            session_id = request.sid
            client_info = {
                'session_id': session_id,
                'connected_at': datetime.utcnow(),
                'user_agent': request.headers.get('User-Agent', ''),
                'ip_address': request.remote_addr,
                'subscribed_tasks': set(),
                'subscribed_rooms': set()
            }
            
            self.connected_clients[session_id] = client_info
            self.client_heartbeats[session_id] = datetime.utcnow()
            
            self.stats['total_connections'] += 1
            self.stats['current_connections'] += 1
            
            logger.info(f"Client {session_id} connected from {client_info['ip_address']}")
            
            # 发送连接确认
            emit('connection_confirmed', {
                'session_id': session_id,
                'server_time': datetime.utcnow().isoformat(),
                'message': 'Connected to Chatlog WebSocket server'
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接事件"""
            session_id = request.sid
            client_info = self.connected_clients.pop(session_id, {})
            
            # 清理订阅
            for task_id in client_info.get('subscribed_tasks', set()):
                self._unsubscribe_task(session_id, task_id)
            
            for room_name in client_info.get('subscribed_rooms', set()):
                self._leave_room(session_id, room_name)
            
            self.client_heartbeats.pop(session_id, None)
            self.stats['current_connections'] -= 1
            
            logger.info(f"Client {session_id} disconnected")
        
        @self.socketio.on('subscribe_task')
        def handle_subscribe_task(data):
            """订阅任务状态更新"""
            session_id = request.sid
            task_id = data.get('task_id')
            
            if not task_id:
                emit('error', {'message': 'Task ID is required'})
                return
            
            self._subscribe_task(session_id, task_id)
            emit('task_subscribed', {
                'task_id': task_id,
                'message': f'Subscribed to task {task_id}'
            })
            
            # 立即发送当前任务状态
            self._send_task_status(task_id)
        
        @self.socketio.on('unsubscribe_task')
        def handle_unsubscribe_task(data):
            """取消订阅任务状态"""
            session_id = request.sid
            task_id = data.get('task_id')
            
            if task_id:
                self._unsubscribe_task(session_id, task_id)
                emit('task_unsubscribed', {
                    'task_id': task_id,
                    'message': f'Unsubscribed from task {task_id}'
                })
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """加入房间"""
            session_id = request.sid
            room_name = data.get('room')
            
            if not room_name:
                emit('error', {'message': 'Room name is required'})
                return
            
            self._join_room(session_id, room_name)
            emit('room_joined', {
                'room': room_name,
                'message': f'Joined room {room_name}'
            })
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """离开房间"""
            session_id = request.sid
            room_name = data.get('room')
            
            if room_name:
                self._leave_room(session_id, room_name)
                emit('room_left', {
                    'room': room_name,
                    'message': f'Left room {room_name}'
                })
        
        @self.socketio.on('heartbeat')
        def handle_heartbeat(data):
            """心跳检测"""
            session_id = request.sid
            self.client_heartbeats[session_id] = datetime.utcnow()
            
            emit('heartbeat_ack', {
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id
            })
        
        @self.socketio.on('get_stats')
        def handle_get_stats():
            """获取WebSocket统计信息"""
            stats = self.get_connection_stats()
            emit('stats_update', stats)
    
    def _subscribe_task(self, session_id: str, task_id: str):
        """订阅任务状态更新"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        
        self.task_subscribers[task_id].add(session_id)
        
        # 更新客户端信息
        if session_id in self.connected_clients:
            self.connected_clients[session_id]['subscribed_tasks'].add(task_id)
    
    def _unsubscribe_task(self, session_id: str, task_id: str):
        """取消订阅任务状态"""
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(session_id)
            
            # 如果没有订阅者了，清理任务
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        
        # 更新客户端信息
        if session_id in self.connected_clients:
            self.connected_clients[session_id]['subscribed_tasks'].discard(task_id)
    
    def _join_room(self, session_id: str, room_name: str):
        """加入房间"""
        join_room(room_name, sid=session_id)
        
        if room_name not in self.room_subscribers:
            self.room_subscribers[room_name] = set()
        
        self.room_subscribers[room_name].add(session_id)
        
        # 更新客户端信息
        if session_id in self.connected_clients:
            self.connected_clients[session_id]['subscribed_rooms'].add(room_name)
    
    def _leave_room(self, session_id: str, room_name: str):
        """离开房间"""
        leave_room(room_name, sid=session_id)
        
        if room_name in self.room_subscribers:
            self.room_subscribers[room_name].discard(session_id)
            
            # 如果房间没有用户了，清理房间
            if not self.room_subscribers[room_name]:
                del self.room_subscribers[room_name]
        
        # 更新客户端信息
        if session_id in self.connected_clients:
            self.connected_clients[session_id]['subscribed_rooms'].discard(room_name)
    
    def _send_task_status(self, task_id: str):
        """发送任务状态更新"""
        try:
            task_queue = get_task_queue()
            task_result = task_queue.get_task_status(task_id)
            
            if task_result and task_id in self.task_subscribers:
                task_data = task_result.to_dict()
                
                # 发送给所有订阅该任务的客户端
                for session_id in self.task_subscribers[task_id].copy():
                    try:
                        self.socketio.emit('task_status_update', {
                            'task_id': task_id,
                            'status': task_data,
                            'timestamp': datetime.utcnow().isoformat()
                        }, room=session_id)
                        
                        self.stats['messages_sent'] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to send task status to {session_id}: {str(e)}")
                        # 移除失效的连接
                        self.task_subscribers[task_id].discard(session_id)
        
        except Exception as e:
            logger.error(f"Failed to send task status for {task_id}: {str(e)}")
    
    def notify_task_update(self, task_id: str):
        """通知任务状态更新"""
        if self.socketio and task_id in self.task_subscribers:
            self._send_task_status(task_id)
    
    def broadcast_to_room(self, room_name: str, event: str, data: Dict[str, Any]):
        """向房间广播消息"""
        try:
            if self.socketio and room_name in self.room_subscribers:
                self.socketio.emit(event, data, room=room_name)
                self.stats['messages_sent'] += len(self.room_subscribers[room_name])
                
        except Exception as e:
            logger.error(f"Failed to broadcast to room {room_name}: {str(e)}")
    
    def send_notification(self, session_id: str, notification_type: str, 
                         title: str, message: str, data: Optional[Dict] = None):
        """发送通知给特定客户端"""
        try:
            if self.socketio and session_id in self.connected_clients:
                notification = {
                    'type': notification_type,
                    'title': title,
                    'message': message,
                    'data': data or {},
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self.socketio.emit('notification', notification, room=session_id)
                self.stats['messages_sent'] += 1
                
        except Exception as e:
            logger.error(f"Failed to send notification to {session_id}: {str(e)}")
    
    def _start_background_tasks(self):
        """启动后台任务"""
        @self.socketio.on('connect')
        def start_task_monitor():
            """启动任务状态监控"""
            def monitor_tasks():
                while True:
                    try:
                        # 检查所有订阅的任务状态
                        for task_id in list(self.task_subscribers.keys()):
                            self._send_task_status(task_id)
                        
                        # 清理过期的心跳连接
                        self._cleanup_stale_connections()
                        
                        time.sleep(2)  # 每2秒检查一次
                        
                    except Exception as e:
                        logger.error(f"Task monitor error: {str(e)}")
                        time.sleep(5)
            
            # 在后台线程中运行监控
            import threading
            monitor_thread = threading.Thread(target=monitor_tasks, daemon=True)
            monitor_thread.start()
    
    def _cleanup_stale_connections(self):
        """清理过期的连接"""
        try:
            current_time = datetime.utcnow()
            stale_threshold = 60  # 60秒无心跳则认为连接过期
            
            stale_sessions = []
            for session_id, last_heartbeat in self.client_heartbeats.items():
                if (current_time - last_heartbeat).total_seconds() > stale_threshold:
                    stale_sessions.append(session_id)
            
            for session_id in stale_sessions:
                logger.info(f"Cleaning up stale connection: {session_id}")
                
                # 清理客户端信息
                client_info = self.connected_clients.pop(session_id, {})
                
                # 清理订阅
                for task_id in client_info.get('subscribed_tasks', set()):
                    self._unsubscribe_task(session_id, task_id)
                
                for room_name in client_info.get('subscribed_rooms', set()):
                    if room_name in self.room_subscribers:
                        self.room_subscribers[room_name].discard(session_id)
                
                self.client_heartbeats.pop(session_id, None)
                self.stats['current_connections'] -= 1
        
        except Exception as e:
            logger.error(f"Failed to cleanup stale connections: {str(e)}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            'connections': self.stats.copy(),
            'active_clients': len(self.connected_clients),
            'active_task_subscriptions': len(self.task_subscribers),
            'active_rooms': len(self.room_subscribers),
            'connected_clients': [
                {
                    'session_id': info['session_id'][:8] + '...',
                    'connected_at': info['connected_at'].isoformat(),
                    'ip_address': info['ip_address'],
                    'subscribed_tasks_count': len(info['subscribed_tasks']),
                    'subscribed_rooms_count': len(info['subscribed_rooms'])
                }
                for info in self.connected_clients.values()
            ]
        }
    
    def shutdown(self):
        """关闭WebSocket服务"""
        try:
            if self.socketio:
                # 通知所有客户端服务即将关闭
                self.socketio.emit('server_shutdown', {
                    'message': 'Server is shutting down',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # 断开所有连接
                for session_id in list(self.connected_clients.keys()):
                    self.socketio.disconnect(session_id)
            
            logger.info("WebSocket manager shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during WebSocket manager shutdown: {str(e)}")


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器实例"""
    return websocket_manager


def init_websocket(app):
    """初始化WebSocket服务"""
    return websocket_manager.init_socketio(app)