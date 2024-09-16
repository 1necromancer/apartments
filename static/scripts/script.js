document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('uploadForm');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const templateSelect = document.getElementById('templateSelect');


    function getListOfTemplates() {
        fetch('/templates/list') // Adjust the URL based on your route to get template names
            .then(response => response.json())
            .then(data => {
                // Assuming 'data' is an array of template names
                data.forEach(templateName => {
                    const option = document.createElement('option');
                    option.value = templateName;
                    option.textContent = templateName;
                    templateSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching template names:', error);
            });
    }

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(form);
        loadingOverlay.classList.add('active');

        fetch('/upload', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (response.redirected) {
                checkProgress();
            }
        });
    });

    function checkProgress() {
        fetch('/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'Processing started') {
                // Update the loading text with real-time progress
                loadingText.textContent = `Идет создание договоров... ${data.processed_files}/${data.total_files}`;
                setTimeout(checkProgress, 1000); // Poll every second
            } else if (data.status === 'Договоры созданы успешно!') {
                loadingText.textContent = `Договоры созданы успешно!`;
                // Hide the loading overlay after success
                setTimeout(() => {
                    loadingOverlay.classList.remove('active');
                }, 1000);
            } else {
                loadingText.textContent = `Error: ${data.status}`;
                // Hide the loading overlay on error
                setTimeout(() => {
                    loadingOverlay.classList.remove('active');
                }, 1000);
            }
        });
    }

    getListOfTemplates();
});