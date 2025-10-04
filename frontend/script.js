let allPosts = [];
let currentPage = 1;
const postsPerPage = 50;

const startDateInput = document.getElementById('startDate');
const endDateInput = document.getElementById('endDate');
const resetButton = document.getElementById('resetButton');
const postCountElement = document.getElementById('postCount');
const currentPageElement = document.getElementById('currentPage');
const totalPagesElement = document.getElementById('totalPages');
const postsContainer = document.getElementById('postsContainer');
const paginationElement = document.getElementById('pagination');

const filterToggle = document.getElementById('filterToggle');
const filterOverlay = document.getElementById('filterOverlay');
const startDatePopup = document.getElementById('startDatePopup');
const endDatePopup = document.getElementById('endDatePopup');
const applyFilter = document.getElementById('applyFilter');
const closeFilter = document.getElementById('closeFilter');

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
    });
}

function getFilteredPosts() {
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;

    return allPosts.filter(post => {
        if (!startDate && !endDate) return true;

        const postDate = new Date(post.date);
        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;

        if (start && end) return postDate >= start && postDate <= end;
        if (start) return postDate >= start;
        if (end) return postDate <= end;
        return true;
    }).sort((a, b) => new Date(b.date) - new Date(a.date));
}

function renderPosts() {
    const filteredPosts = getFilteredPosts();
    const totalPages = Math.ceil(filteredPosts.length / postsPerPage);
    const currentPosts = filteredPosts.slice(
        (currentPage - 1) * postsPerPage,
        currentPage * postsPerPage
    );

    postCountElement.textContent = filteredPosts.length;
    currentPageElement.textContent = currentPage;
    totalPagesElement.textContent = totalPages;

    postsContainer.innerHTML = currentPosts.map(post => `
        <div class="post-card fade-in">
            <div class="post-content">
                <div class="post-header">
                    <h3 class="post-title">${post.title}</h3>
                    <div class="post-date">${formatDate(post.date)}</div>
                </div>
                <p class="post-excerpt">${post.excerpt}</p>
                <a href="${post.source}" target="_blank" class="read-more">
                    Читать далее →
                </a>
            </div>
        </div>
    `).join('');

    renderPagination(totalPages);

    if (startDateInput.value || endDateInput.value) {
        resetButton.classList.remove('hidden');
    } else {
        resetButton.classList.add('hidden');
    }
}

function renderPagination(totalPages) {
    if (totalPages <= 1) {
        paginationElement.classList.add('hidden');
        return;
    }

    paginationElement.classList.remove('hidden');

    let paginationHTML = '';

    paginationHTML += `
        <button class="page-btn ${currentPage === 1 ? 'disabled' : ''}"
                onclick="changePage(${currentPage - 1})"
                ${currentPage === 1 ? 'disabled' : ''}>
            Назад
        </button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        paginationHTML += `
            <button class="page-btn ${currentPage === i ? 'active' : ''}"
                    onclick="changePage(${i})">
                ${i}
            </button>
        `;
    }

    paginationHTML += `
        <button class="page-btn ${currentPage === totalPages ? 'disabled' : ''}"
                onclick="changePage(${currentPage + 1})"
                ${currentPage === totalPages ? 'disabled' : ''}>
            Вперед
        </button>
    `;

    paginationElement.innerHTML = paginationHTML;
}

function changePage(page) {
    const filteredPosts = getFilteredPosts();
    const totalPages = Math.ceil(filteredPosts.length / postsPerPage);

    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        renderPosts();
    }
}

// Reset filters
function resetFilters() {
    startDateInput.value = '';
    endDateInput.value = '';
    currentPage = 1;
    renderPosts();
}

startDateInput.addEventListener('change', () => { currentPage = 1; renderPosts(); });
endDateInput.addEventListener('change', () => { currentPage = 1; renderPosts(); });
resetButton.addEventListener('click', resetFilters);

filterToggle.addEventListener('click', () => {
    filterOverlay.classList.remove('hidden');
});

closeFilter.addEventListener('click', () => {
    filterOverlay.classList.add('hidden');
});

applyFilter.addEventListener('click', () => {
    startDateInput.value = startDatePopup.value;
    endDateInput.value = endDatePopup.value;
    currentPage = 1;
    renderPosts();
    filterOverlay.classList.add('hidden');
});

const socket = new WebSocket("ws://localhost:8000/ws/posts");

socket.onmessage = (event) => {
    allPosts = JSON.parse(event.data);
    console.log("Полученные посты:", allPosts);

    currentPage = 1;
    renderPosts();
};

socket.onopen = () => {
    console.log("✅ WebSocket подключен");
};

socket.onerror = (error) => {
    console.error("❌ WebSocket ошибка:", error);
};

socket.onclose = () => {
    console.log("⚠️ WebSocket закрыт");
};
