document.addEventListener('DOMContentLoaded', () => {
    // Авто-закрытие flash-сообщений через 5 секунд
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => {
            el.style.transition = 'opacity .4s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 400);
        }, 5000);
    });
});

// ===== ПЕРЕКЛЮЧАТЕЛЬ ТЕМ =====

function setTheme(name) {
    document.documentElement.setAttribute('data-theme', name);
    localStorage.setItem('ab_theme', name);
    document.querySelectorAll('[data-theme-btn]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.themeBtn === name);
    });
}

// Применяем сохранённую тему сразу при загрузке скрипта
(function() {
    const saved = localStorage.getItem('ab_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-theme-btn]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.themeBtn === saved);
        });
    });
})();