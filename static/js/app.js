const searchInput = document.getElementById("searchInput");
const categoryFilter = document.getElementById("categoryFilter");
const typeFilter = document.getElementById("typeFilter");
const noiseFilter = document.getElementById("noiseFilter");
const dayFilter = document.getElementById("dayFilter");
const groupSizeInput = document.getElementById("groupSizeInput");
const decreaseGroup = document.getElementById("decreaseGroup");
const increaseGroup = document.getElementById("increaseGroup");

const cards = document.querySelectorAll(".space-card");
const analysisPanel = document.getElementById("analysisPanel");

let selectedSpace = null;

function usageStatus(count) {
    if (count <= 4) {
        return {
            label: "Low usage",
            className: "good",
            text: "This space looks lightly used based on the current sample check-in count."
        };
    }

    if (count <= 9) {
        return {
            label: "Moderate usage",
            className: "warning",
            text: "This space may still be usable, but people may need to share or rotate."
        };
    }

    return {
        label: "High usage",
        className: "danger",
        text: "This space may be crowded based on the current sample check-in count."
    };
}

function noiseDescription(noiseLevel) {
    if (noiseLevel === "Quiet") {
        return "Best for focused work, reading, or studying alone.";
    }

    if (noiseLevel === "Moderate") {
        return "Good for casual work, light conversation, or studying with a few people.";
    }

    if (noiseLevel === "Loud") {
        return "Better for social studying or groups that do not need a quiet environment.";
    }

    return "Noise level information is not available for this space.";
}

function filterCards() {
    const searchText = searchInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value;
    const selectedType = typeFilter.value;
    const selectedNoise = noiseFilter.value;
    const selectedDay = dayFilter.value;

    cards.forEach(card => {
        const space = JSON.parse(card.dataset.space);

        const nameMatches = space.name.toLowerCase().includes(searchText);
        const categoryMatches = selectedCategory === "all" || space.category === selectedCategory;
        const typeMatches = selectedType === "all" || space.facility_type === selectedType;
        const noiseMatches = selectedNoise === "all" || space.noise_level === selectedNoise;
        const dayMatches = selectedDay === "all" || space.schedule.some(item => item.day === selectedDay);

        card.style.display =
            nameMatches &&
            categoryMatches &&
            typeMatches &&
            noiseMatches &&
            dayMatches
                ? "block"
                : "none";
    });
}

function showAnalysis(space) {
    selectedSpace = space;

    const groupSize = Number(groupSizeInput.value || 1);
    const usage = usageStatus(space.current_count);

    const groupClass = groupSize > space.group_size_limit ? "danger" : "good";
    const groupMessage = groupSize > space.group_size_limit
        ? `Your group size is ${groupSize}. This is over the listed group limit of ${space.group_size_limit}, so staff approval, reservation guidance, or a different space may be needed.`
        : `Your group size is ${groupSize}, which is within the listed group limit of ${space.group_size_limit}.`;

    const selectedDay = dayFilter.value;
    const schedule = selectedDay === "all"
        ? space.schedule
        : space.schedule.filter(item => item.day === selectedDay);

    const scheduleHtml = schedule.length
        ? schedule.map(item => `<li><strong>${item.day}:</strong> ${item.time} — ${item.status}</li>`).join("")
        : "<li>No sample schedule data for this selected day.</li>";

    analysisPanel.innerHTML = `
        <p class="tag">Space Analysis</p>
        <h2>${space.name}</h2>
        <p class="muted">${space.location} · ${space.category} · ${space.facility_type}</p>

        <div class="analysis-box ${usage.className}">
            <strong>${usage.label}</strong>
            <p>${usage.text}</p>
            <p><strong>Current sample check-ins:</strong> ${space.current_count}</p>
        </div>

        <div class="analysis-box">
            <strong>Noise Level: ${space.noise_level}</strong>
            <p>${noiseDescription(space.noise_level)}</p>
        </div>

        <div class="analysis-box ${groupClass}">
            <strong>Group Size Check</strong>
            <p>${groupMessage}</p>
        </div>

        <div class="analysis-box">
            <strong>Rules</strong>
            <ul>
                <li><strong>Cost:</strong> ${space.cost_status}</li>
                <li><strong>Use Type:</strong> ${space.reservation_type}</li>
                <li><strong>Restrictions:</strong> ${space.restrictions}</li>
                <li><strong>Notes:</strong> ${space.rule_notes}</li>
            </ul>
        </div>

        <div class="analysis-box">
            <strong>Schedule / Availability Notes</strong>
            <ul>${scheduleHtml}</ul>
            <p class="muted">This is demo schedule information, not live official availability.</p>
        </div>

        <div class="analysis-box">
            <strong>Next Step</strong>
            <p>${space.next_step}</p>
        </div>
    `;
}

function updateGroupSize(amount) {
    let current = Number(groupSizeInput.value || 1);
    current += amount;

    if (current < 1) {
        current = 1;
    }

    groupSizeInput.value = current;

    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
}

cards.forEach(card => {
    const button = card.querySelector(".analysis-button");

    button.addEventListener("click", () => {
        const space = JSON.parse(card.dataset.space);
        showAnalysis(space);
    });
});

searchInput.addEventListener("input", filterCards);
categoryFilter.addEventListener("change", filterCards);
typeFilter.addEventListener("change", filterCards);
noiseFilter.addEventListener("change", filterCards);

dayFilter.addEventListener("change", () => {
    filterCards();

    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
});

groupSizeInput.addEventListener("input", () => {
    if (Number(groupSizeInput.value) < 1) {
        groupSizeInput.value = 1;
    }

    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
});

decreaseGroup.addEventListener("click", () => updateGroupSize(-1));
increaseGroup.addEventListener("click", () => updateGroupSize(1));