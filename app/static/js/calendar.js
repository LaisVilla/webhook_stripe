document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'pt-br',
        height: 'auto',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        buttonText: {
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
            day: 'Dia'
        },
        events: '/api/events',
        editable: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false,
            hour12: false
        },
        select: function(info) {
            showEventModal(null, info);
        },
        eventClick: function(info) {
            showEventModal(info.event);
        },
        eventDidMount: function(info) {
            // Adiciona tooltip aos eventos
            tippy(info.el, {
                content: info.event.title,
                theme: 'dark',
            });
        }
    });
    
    calendar.render();
    
    // Gerenciamento do Modal
    const eventModal = document.getElementById('eventModal');
    const eventForm = document.getElementById('eventForm');
    let currentEvent = null;
    
    window.showEventModal = function(event, dateInfo) {
        const titleInput = document.getElementById('title');
        const startInput = document.getElementById('start');
        const endInput = document.getElementById('end');
        const descriptionInput = document.getElementById('description');
        
        if (event) {
            // Editar evento existente
            currentEvent = event;
            titleInput.value = event.title;
            startInput.value = event.start ? formatDateTime(event.start) : '';
            endInput.value = event.end ? formatDateTime(event.end) : '';
            descriptionInput.value = event.extendedProps.description || '';
        } else {
            // Novo evento
            currentEvent = null;
            titleInput.value = '';
            if (dateInfo) {
                startInput.value = formatDateTime(dateInfo.start);
                endInput.value = dateInfo.allDay ? formatDateTime(dateInfo.end) : '';
            } else {
                startInput.value = '';
                endInput.value = '';
            }
            descriptionInput.value = '';
        }
        
        eventModal.classList.remove('hidden');
    }
    
    window.closeEventModal = function() {
        eventModal.classList.add('hidden');
        currentEvent = null;
    }
    
    eventForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const eventData = {
            title: document.getElementById('title').value,
            start_time: document.getElementById('start').value,
            end_time: document.getElementById('end').value || document.getElementById('start').value,
            description: document.getElementById('description').value
        };
        
        const method = currentEvent ? 'PUT' : 'POST';
        const url = currentEvent ? `/api/events/${currentEvent.id}` : '/api/events';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(eventData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                calendar.refetchEvents();
                closeEventModal();
                // Mostrar notificação de sucesso
                showNotification('Evento salvo com sucesso!', 'success');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Erro ao salvar evento.', 'error');
        });
    });
});

// Função auxiliar para formatar data e hora
function formatDateTime(date) {
    const d = new Date(date);
    return d.toISOString().slice(0, 16);
}

// Função para mostrar notificações
function showNotification(message, type = 'success') {
    const notificationDiv = document.createElement('div');
    notificationDiv.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    } text-white z-50 animate-fade-in-up`;
    notificationDiv.textContent = message;
    
    document.body.appendChild(notificationDiv);
    
    setTimeout(() => {
        notificationDiv.remove();
    }, 3000);
}

// Adicionar animações CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(1rem);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-fade-in-up {
        animation: fadeInUp 0.3s ease-out;
    }
`;
document.head.appendChild(style);