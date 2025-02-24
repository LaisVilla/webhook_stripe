document.addEventListener('DOMContentLoaded', function () {
    loadTasks();
    setupTaskForm();
    setupDragAndDrop();
});

// Configuração de ícones Lucide
function setupEventListeners() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// Configuração do Drag and Drop
function setupDragAndDrop() {
    const containers = document.querySelectorAll('.task-container');
    containers.forEach(container => {
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            container.classList.add('drag-over');
        });

        container.addEventListener('dragleave', (e) => {
            if (!container.contains(e.relatedTarget)) {
                container.classList.remove('drag-over');
            }
        });

        container.addEventListener('drop', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');

            const taskId = e.dataTransfer.getData('text/plain');
            const newStatus = container.getAttribute('data-status');
            const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);

            if (taskElement && taskElement.getAttribute('data-status') !== newStatus) {
                fetch(`/api/tasks/${taskId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        status: newStatus
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            loadTasks(); // Recarrega todas as tarefas
                            showNotification('Tarefa movida com sucesso!', 'success');
                        } else {
                            throw new Error(data.message || 'Erro ao atualizar status');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showNotification('Erro ao mover tarefa', 'error');
                    });
            }
        });
    });
}

function createTaskElement(task) {
    const div = document.createElement('div');
    div.className = 'task-card bg-[#0F172A] rounded-xl shadow-lg border border-gray-700 p-5 hover:border-gray-500 transition-all duration-200';
    div.draggable = true;
    div.setAttribute('data-task-id', task.task_id);
    div.setAttribute('data-status', task.status);

    div.addEventListener('dragstart', (e) => {
        e.target.classList.add('dragging');
        e.dataTransfer.setData('text/plain', task.task_id);
    });

    div.addEventListener('dragend', (e) => {
        e.target.classList.remove('dragging');
        document.querySelectorAll('.task-container').forEach(container => {
            container.classList.remove('drag-over');
        });
    });

    const priorityColors = {
        low: 'bg-green-500/20 text-green-500',
        medium: 'bg-yellow-500/20 text-yellow-500',
        high: 'bg-red-500/20 text-red-500'
    };

    const priorityLabels = {
        low: 'Baixa',
        medium: 'Média',
        high: 'Alta'
    };

    const statusIcons = {
        pending: 'clock',
        in_progress: 'loader-2',
        completed: 'check-circle'
    };

    const statusColors = {
        pending: 'text-yellow-500',
        in_progress: 'text-blue-500',
        completed: 'text-green-500'
    };

    const formattedDate = task.due_date ? new Date(task.due_date).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) : '';

    div.innerHTML = `
        <div class="flex flex-col gap-3">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-2">
                        <i class="lucide lucide-${statusIcons[task.status] || 'help-circle'} h-5 w-5 ${statusColors[task.status]}"></i>
                        <h3 class="font-semibold text-white text-lg">${task.title || 'Sem título'}</h3>
                    </div>
                    ${task.description ? `
                        <p class="text-gray-400 text-sm mt-2">${task.description}</p>
                    ` : ''}
                </div>
                <button type="button" 
                    onclick="editTask('${task.task_id}')"
                    class="edit-btn flex items-center gap-2 px-3 py-2 bg-gray-700/50 hover:bg-gray-600 
                        text-gray-300 hover:text-white rounded-lg transition-all duration-200">
                    <i class="lucide lucide-pencil h-4 w-4"></i>
                    <span class="text-sm">Editar</span>
                </button>
            </div>
            <div class="flex items-center justify-between mt-2">
                <div class="flex items-center gap-2">
                    <span class="${priorityColors[task.priority] || priorityColors.medium} text-xs px-3 py-1 rounded-full">
                        ${priorityLabels[task.priority] || 'Média'}
                    </span>
                    ${formattedDate ? `
                        <span class="text-gray-400 text-sm flex items-center gap-1">
                            <i class="lucide lucide-calendar h-4 w-4"></i>
                            ${formattedDate}
                        </span>
                    ` : ''}
                </div>
            </div>
        </div>
    `;

    return div;
}

// Função para carregar tarefas
function loadTasks() {
    fetch('/api/tasks')
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao carregar tarefas');
            }
            return response.json();
        })
        .then(tasks => {
            ['pending', 'in-progress', 'completed'].forEach(status => {
                const countElement = document.getElementById(`${status}-count`);
                const container = document.getElementById(`${status}-tasks`);

                if (countElement) countElement.textContent = '0';
                if (container) container.innerHTML = '';
            });

            const tasksByStatus = {
                pending: [],
                in_progress: [],
                completed: []
            };

            tasks.forEach(task => {
                const status = task.status || 'pending';
                if (tasksByStatus[status]) {
                    tasksByStatus[status].push(task);
                } else {
                    tasksByStatus.pending.push(task);
                }
            });

            Object.keys(tasksByStatus).forEach(status => {
                const tasksForStatus = tasksByStatus[status];
                const countElement = document.getElementById(`${status.replace('_', '-')}-count`);
                const container = document.getElementById(`${status.replace('_', '-')}-tasks`);

                if (countElement) {
                    countElement.textContent = tasksForStatus.length;
                }

                if (container) {
                    if (tasksForStatus.length === 0) {
                        container.innerHTML = `
                            <div class="text-gray-500 text-center py-8 border-2 border-dashed border-gray-700 rounded-xl">
                                <i class="lucide lucide-inbox h-6 w-6 mx-auto mb-2"></i>
                                <p>Nenhuma tarefa ${status === 'pending' ? 'pendente' :
                                status === 'in_progress' ? 'em andamento' : 'concluída'}</p>
                            </div>
                        `;
                    } else {
                        tasksForStatus.forEach(task => {
                            container.appendChild(createTaskElement(task));
                        });
                    }
                }
            });

            setupEventListeners();
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Erro ao carregar tarefas', 'error');
        });
}

// Configurar formulário
function setupTaskForm() {
    const taskForm = document.getElementById('taskForm');
    // Definir currentTask no escopo externo para ser acessível   por todas as funções
    window.currentTask = null;

    window.showTaskModal = function(taskId = null) {
        // Corrigindo a seleção do título do modal
        const modalTitle = document.querySelector('#taskModal h3 span');
        const deleteButton = document.getElementById('deleteTaskButton');
        const statusSelect = document.getElementById('taskStatus');

        if (taskId) {
            console.log('Editando tarefa:', taskId);
            fetch(`/api/tasks/${taskId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erro ao carregar tarefa');
                    }
                    return response.json();
                })
                .then(task => {
                    console.log('Dados da tarefa:', task);
                    window.currentTask = task;
                    
                    // Atualizar título do modal
                    if (modalTitle) {
                        modalTitle.textContent = 'Editar Tarefa';
                    }

                    // Preencher campos do formulário
                    const titleInput = document.getElementById('taskTitle');
                    const descriptionInput = document.getElementById('taskDescription');
                    const dueDateInput = document.getElementById('taskDueDate');
                    const prioritySelect = document.getElementById('taskPriority');
                    const statusSelect = document.getElementById('taskStatus');

                    if (titleInput) titleInput.value = task.title || '';
                    if (descriptionInput) descriptionInput.value = task.description || '';
                    if (dueDateInput && task.due_date) {
                        // Formatando a data para o formato aceito pelo input datetime-local
                        const date = new Date(task.due_date);
                        const formattedDate = date.toISOString().slice(0, 16);
                        dueDateInput.value = formattedDate;
                    }
                    if (prioritySelect) prioritySelect.value = task.priority || 'medium';
                    if (statusSelect) {
                        statusSelect.value = task.status || 'pending';
                        statusSelect.removeAttribute('disabled');
                    }

                    // Mostrar botão de deletar
                    if (deleteButton) {
                        deleteButton.classList.remove('hidden');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Erro ao carregar tarefa', 'error');
                });
        } else {
            // Nova tarefa
            if (modalTitle) {
                modalTitle.textContent = 'Nova Tarefa';
            }
            taskForm.reset();
            currentTask = null;
            
            if (deleteButton) {
                deleteButton.classList.add('hidden');
            }
            if (statusSelect) {
                statusSelect.value = 'pending';
                statusSelect.setAttribute('disabled', 'disabled');
            }

            const prioritySelect = document.getElementById('taskPriority');
            if (prioritySelect) {
                prioritySelect.value = 'medium';
            }
        }

        // Mostrar modal
        const modal = document.getElementById('taskModal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    window.closeTaskModal = function() {
        const modal = document.getElementById('taskModal');
        if (modal) {
            modal.classList.add('hidden');
            currentTask = null;
            taskForm.reset();
        }
    }

    window.editTask = function(taskId) {
        console.log('Iniciando edição da tarefa:', taskId);
        showTaskModal(taskId);
    }

    // Adicionar event listener para o formulário
    if (taskForm) {
        taskForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const taskData = {
                title: document.getElementById('taskTitle').value.trim(),
                description: document.getElementById('taskDescription').value.trim(),
                due_date: document.getElementById('taskDueDate').value,
                priority: document.getElementById('taskPriority').value,
                status: document.getElementById('taskStatus').value
            };

            const method = window.currentTask ? 'PUT' : 'POST';
            const url = window.currentTask ? `/api/tasks/${window.currentTask.task_id}` : '/api/tasks';

            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(taskData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    loadTasks();
                    closeTaskModal();
                    showNotification(
                        currentTask ? 'Tarefa atualizada com sucesso!' : 'Tarefa criada com sucesso!',
                        'success'
                    );
                } else {
                    throw new Error(data.message || 'Erro ao salvar tarefa');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erro ao salvar tarefa', 'error');
            });
        });
    }
}

window.deleteTask = function() {
    if (!currentTask || !currentTask.task_id) {
        console.error('Nenhuma tarefa selecionada para excluir');
        showNotification('Erro: Nenhuma tarefa selecionada', 'error');
        return;
    }
    
    console.log('Tentando excluir tarefa:', currentTask.task_id);
    
    if (confirm('Tem certeza que deseja excluir esta tarefa?')) {
        fetch(`/api/tasks/${currentTask.task_id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao excluir tarefa');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                loadTasks();
                closeTaskModal();
                showNotification('Tarefa excluída com sucesso!', 'success');
            } else {
                throw new Error(data.message || 'Erro ao excluir tarefa');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Erro ao excluir tarefa', 'error');
        });
    }
}

// Mostrar notificações
function showNotification(message, type = 'success') {
    const notificationDiv = document.createElement('div');
    notificationDiv.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg ${type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white z-50`;
    notificationDiv.textContent = message;

    document.body.appendChild(notificationDiv);

    setTimeout(() => {
        notificationDiv.remove();
    }, 3000);
}

// Adicionar estilos CSS para as animações
const style = document.createElement('style');
style.textContent = `
    .task-card {
        transition: all 0.3s ease;
        cursor: grab;
    }
    
    .task-card.dragging {
        opacity: 0.5;
        transform: scale(0.95);
        cursor: grabbing;
    }
    
    .task-container.drag-over {
        border: 2px dashed rgba(139, 92, 246, 0.5);
        background-color: rgba(139, 92, 246, 0.1);
    }
`;
document.head.appendChild(style);