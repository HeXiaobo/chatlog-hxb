/**
 * WebSocket Hook - 实时通信和任务状态监听
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import io, { Socket } from 'socket.io-client'

export interface TaskStatus {
  task_id: string
  status: {
    status: string
    result?: any
    error?: string
    start_time?: string
    end_time?: string
    execution_time?: number
    retry_count?: number
  }
  timestamp: string
}

export interface WebSocketStats {
  connections: {
    total_connections: number
    current_connections: number
    messages_sent: number
    messages_received: number
  }
  active_clients: number
  active_task_subscriptions: number
  active_rooms: number
}

interface UseWebSocketOptions {
  url?: string
  autoConnect?: boolean
  reconnectAttempts?: number
  reconnectDelay?: number
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    url = process.env.NODE_ENV === 'production' 
      ? window.location.origin 
      : 'http://localhost:5000',
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectDelay = 1000
  } = options

  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [taskStatuses, setTaskStatuses] = useState<Map<string, TaskStatus>>(new Map())
  const [notifications, setNotifications] = useState<any[]>([])
  
  const reconnectCount = useRef(0)
  const subscribedTasks = useRef<Set<string>>(new Set())
  const joinedRooms = useRef<Set<string>>(new Set())

  // 连接WebSocket
  const connect = useCallback(() => {
    try {
      const newSocket = io(url, {
        transports: ['websocket', 'polling'],
        timeout: 20000,
        autoConnect: false
      })

      // 连接事件
      newSocket.on('connect', () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionError(null)
        reconnectCount.current = 0
        
        // 重新订阅之前的任务和房间
        subscribedTasks.current.forEach(taskId => {
          newSocket.emit('subscribe_task', { task_id: taskId })
        })
        
        joinedRooms.current.forEach(room => {
          newSocket.emit('join_room', { room })
        })
      })

      newSocket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason)
        setIsConnected(false)
        
        // 自动重连
        if (reason !== 'io client disconnect' && reconnectCount.current < reconnectAttempts) {
          setTimeout(() => {
            reconnectCount.current += 1
            console.log(`Attempting to reconnect... (${reconnectCount.current}/${reconnectAttempts})`)
            newSocket.connect()
          }, reconnectDelay * reconnectCount.current)
        }
      })

      newSocket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error)
        setConnectionError(error.message)
        setIsConnected(false)
      })

      // 任务状态更新
      newSocket.on('task_status_update', (data: TaskStatus) => {
        console.log('Task status update:', data)
        setTaskStatuses(prev => new Map(prev.set(data.task_id, data)))
      })

      // 通知消息
      newSocket.on('notification', (notification) => {
        console.log('Notification received:', notification)
        setNotifications(prev => [...prev, notification])
      })

      // 心跳应答
      newSocket.on('heartbeat_ack', (data) => {
        console.log('Heartbeat ack:', data)
      })

      // 连接确认
      newSocket.on('connection_confirmed', (data) => {
        console.log('Connection confirmed:', data)
      })

      // 服务器关闭通知
      newSocket.on('server_shutdown', (data) => {
        console.warn('Server shutdown notification:', data)
        setConnectionError('服务器正在关闭')
      })

      setSocket(newSocket)
      
      if (autoConnect) {
        newSocket.connect()
      }

      return newSocket
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionError(error instanceof Error ? error.message : '连接失败')
      return null
    }
  }, [url, autoConnect, reconnectAttempts, reconnectDelay])

  // 断开连接
  const disconnect = useCallback(() => {
    if (socket) {
      socket.disconnect()
      setSocket(null)
      setIsConnected(false)
      subscribedTasks.current.clear()
      joinedRooms.current.clear()
    }
  }, [socket])

  // 订阅任务状态
  const subscribeToTask = useCallback((taskId: string) => {
    if (socket && isConnected) {
      socket.emit('subscribe_task', { task_id: taskId })
      subscribedTasks.current.add(taskId)
      console.log(`Subscribed to task: ${taskId}`)
    }
  }, [socket, isConnected])

  // 取消订阅任务
  const unsubscribeFromTask = useCallback((taskId: string) => {
    if (socket && isConnected) {
      socket.emit('unsubscribe_task', { task_id: taskId })
      subscribedTasks.current.delete(taskId)
      console.log(`Unsubscribed from task: ${taskId}`)
    }
  }, [socket, isConnected])

  // 加入房间
  const joinRoom = useCallback((room: string) => {
    if (socket && isConnected) {
      socket.emit('join_room', { room })
      joinedRooms.current.add(room)
      console.log(`Joined room: ${room}`)
    }
  }, [socket, isConnected])

  // 离开房间
  const leaveRoom = useCallback((room: string) => {
    if (socket && isConnected) {
      socket.emit('leave_room', { room })
      joinedRooms.current.delete(room)
      console.log(`Left room: ${room}`)
    }
  }, [socket, isConnected])

  // 发送心跳
  const sendHeartbeat = useCallback(() => {
    if (socket && isConnected) {
      socket.emit('heartbeat', { timestamp: new Date().toISOString() })
    }
  }, [socket, isConnected])

  // 获取WebSocket统计信息
  const getStats = useCallback(() => {
    if (socket && isConnected) {
      socket.emit('get_stats')
    }
  }, [socket, isConnected])

  // 清除通知
  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // 清除任务状态
  const clearTaskStatus = useCallback((taskId: string) => {
    setTaskStatuses(prev => {
      const newMap = new Map(prev)
      newMap.delete(taskId)
      return newMap
    })
  }, [])

  // 初始化连接
  useEffect(() => {
    const socketInstance = connect()
    
    return () => {
      if (socketInstance) {
        socketInstance.disconnect()
      }
    }
  }, [connect])

  // 定时发送心跳
  useEffect(() => {
    if (isConnected) {
      const heartbeatInterval = setInterval(sendHeartbeat, 30000) // 每30秒发送心跳
      return () => clearInterval(heartbeatInterval)
    }
  }, [isConnected, sendHeartbeat])

  return {
    // 连接状态
    isConnected,
    connectionError,
    socket,
    
    // 连接管理
    connect,
    disconnect,
    
    // 任务管理
    subscribeToTask,
    unsubscribeFromTask,
    taskStatuses,
    clearTaskStatus,
    
    // 房间管理
    joinRoom,
    leaveRoom,
    
    // 通知管理
    notifications,
    clearNotifications,
    
    // 工具方法
    sendHeartbeat,
    getStats,
    
    // 状态数据
    subscribedTaskIds: Array.from(subscribedTasks.current),
    joinedRooms: Array.from(joinedRooms.current)
  }
}

// 任务状态监听Hook
export const useTaskStatus = (taskId: string | null) => {
  const { subscribeToTask, unsubscribeFromTask, taskStatuses, clearTaskStatus } = useWebSocket()
  
  useEffect(() => {
    if (taskId) {
      subscribeToTask(taskId)
      
      return () => {
        unsubscribeFromTask(taskId)
      }
    }
  }, [taskId, subscribeToTask, unsubscribeFromTask])

  const taskStatus = taskId ? taskStatuses.get(taskId) : null
  
  return {
    taskStatus,
    isLoading: taskStatus?.status.status === 'running',
    isCompleted: taskStatus?.status.status === 'completed',
    isFailed: taskStatus?.status.status === 'failed',
    error: taskStatus?.status.error,
    result: taskStatus?.status.result,
    clearStatus: () => taskId && clearTaskStatus(taskId)
  }
}

export default useWebSocket