import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainButton } from '@vkruglikov/react-telegram-web-app';

function ServiceList() {
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Загрузка списка услуг
    fetch('/api/v1/services')
      .then(response => response.json())
      .then(data => setServices(data))
      .catch(error => console.error('Error:', error));
  }, []);

  const handleServiceSelect = (service) => {
    setSelectedService(service);
  };

  const handleBooking = () => {
    if (selectedService) {
      navigate(`/appointment/${selectedService.id}`);
    }
  };

  return (
    <div className="service-list">
      <h2>Наши услуги</h2>
      <div className="services">
        {services.map(service => (
          <div
            key={service.id}
            className={`service-item ${selectedService?.id === service.id ? 'selected' : ''}`}
            onClick={() => handleServiceSelect(service)}
          >
            <h3>{service.name}</h3>
            <p>{service.description}</p>
            <p className="price">{service.price} ₽</p>
            <p className="duration">{service.duration} мин</p>
          </div>
        ))}
      </div>
      {selectedService && (
        <MainButton text="Записаться" onClick={handleBooking} />
      )}
    </div>
  );
}

export default ServiceList;