// static/js/stats.js
document.addEventListener('DOMContentLoaded', function() {
    const statsControls = document.querySelector('.stats-controls');
    if (!statsControls) return; // Exit if not on the details page

    statsControls.addEventListener('click', (e) => {
        if (e.target.matches('.tab-btn') && !e.target.classList.contains('active-tab')) {
            const period = e.target.id.replace('tab-', '');
            
            // Update button appearance
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active-tab');
            });
            e.target.classList.add('active-tab');

            // Show/hide the correct stat windows
            document.querySelectorAll('.stat-window').forEach(el => {
                el.style.display = 'none';
            });
            document.querySelectorAll(`.stat-${period}`).forEach(el => {
                el.style.display = el.classList.contains('team-comparison') ? 'flex' : 'block';
            });
        }
    });
});
