import { useState, useEffect, useRef, useCallback } from "react";
import NotificationContext from "./NotificationContext";
import { notificationService } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { getToken } from "../utils/jwt";

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const { isAuthenticated, user } = useAuth();

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const response = await notificationService.getAll(30, 0);
      setNotifications(response.data.notifications || []);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await notificationService.getUnreadCount();
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error("Failed to fetch unread count:", error);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (!isAuthenticated || !user) return;

    const token = getToken();
    if (!token) return;

    // Extract user_id from JWT payload
    let userId;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      userId = payload.user_id || payload.id;
    } catch {
      return;
    }

    if (!userId) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `ws://localhost:8005/api/v1/notifications/ws?user_id=${userId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("[WS] Connected to notification service");
    };

    ws.onmessage = (event) => {
      try {
        const notification = JSON.parse(event.data);
        setNotifications((prev) => [notification, ...prev]);
        setUnreadCount((prev) => prev + 1);
      } catch (error) {
        console.error("[WS] Failed to parse message:", error);
      }
    };

    ws.onclose = () => {
      console.log("[WS] Disconnected from notification service");
      // Reconnect after 5 seconds
      reconnectTimerRef.current = setTimeout(() => {
        if (isAuthenticated) {
          connectWebSocket();
        }
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error("[WS] WebSocket error:", error);
    };

    wsRef.current = ws;
  }, [isAuthenticated, user]);

  // Connect WebSocket and fetch initial data when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
      fetchUnreadCount();
      connectWebSocket();
    } else {
      // Cleanup on logout
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      setNotifications([]);
      setUnreadCount(0);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [isAuthenticated, connectWebSocket, fetchNotifications, fetchUnreadCount]);

  const markAsRead = async (id) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all as read:", error);
    }
  };

  const deleteNotification = async (id) => {
    try {
      await notificationService.delete(id);
      const removed = notifications.find((n) => n.id === id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (removed && !removed.read) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error("Failed to delete notification:", error);
    }
  };

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        loading,
        markAsRead,
        markAllAsRead,
        deleteNotification,
        fetchNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};
