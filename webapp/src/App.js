import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import WebApp from '@twa-dev/sdk';
import { MainButton } from '@vkruglikov/react-telegram-web-app';
import ServiceList from './components/ServiceList';
import AppointmentForm from './components/AppointmentForm';
import AdminPanel from './components/AdminPanel';

function App() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Получаем данные пользователя из Telegram WebApp
    const initData = WebApp.initData || '';
    const user = WebApp.initDataUnsafe?.user;
    setUser(user);

    // Проверяем, является ли пользователь администратором
    if (user) {
      fetch(`/api/v1/admin/check/${user.id}`)
        .then(response => response.json())
        .then(data => setIsAdmin(data.is_admin))
        .catch(error => console.error('Error:', error));
    }
  }, []);

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/" 
            element={isAdmin ? <AdminPanel /> : <ServiceList />} 
          />
          <Route 
            path="/appointment/:serviceId" 
            element={<AppointmentForm user={user} />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;