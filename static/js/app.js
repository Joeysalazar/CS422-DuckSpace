/*
File: static/js/app.js
Purpose:
    Handles the interactive parts of the Duck Space homepage.

    This file controls search, filters, group-size buttons, space cards,
    and the analysis panel. The cards are loaded by Flask, but when the user
    clicks "View Analysis", this JavaScript asks the backend API for more
    detailed rule, schedule, hours, check-in, and group-size information.

System:
    Duck Space is a CS 422 student project that helps students compare campus
    spaces by rules, schedule notes, group-size guidance, and next steps.

Authors:
    Initial UI: Joey Salazar
    Backend integration update: Joey Salazar

Last updated:
    May 2026
*/


// ---------------------------------------------------------------------
// Page elements
// ---------------------------------------------------------------------

// Search input used to filter spaces by name.
const searchInput = document.getElementById("searchInput");

// Dropdown used to filter spaces by broad category.
const categoryFilter = document.getElementById("categoryFilter");

// Dropdown used to filter spaces by facility type, such as Court or Studio.
const typeFilter = document.getElementById("typeFilter");

// Dropdown used to filter spaces by estimated noise level.
const noiseFilter = document.getElementById("noiseFilter");

// Dropdown used to filter schedule information by day.
const dayFilter = document.getElementById("dayFilter");

// Number input used to check whether a group size needs extra guidance.
const groupSizeInput = document.getElementById("groupSizeInput");

// Button that decreases the selected group size.
const decreaseGroup = document.getElementById("decreaseGroup");

// Button that increases the selected group size.
const increaseGroup = document.getElementById("increaseGroup");

// All facility cards currently shown on the homepage.
const cards = document.querySelectorAll(".space-card");

// Right-side panel where the selected facility analysis appears.
const analysisPanel = document.getElementById("analysisPanel");

// Stores the most recently selected space.
// This lets the page refresh the same analysis when group size or day changes.
let selectedSpace = null;


// ---------------------------------------------------------------------
// Display helper functions
// ---------------------------------------------------------------------

function usageStatus(count) {
    /*
    Decide how crowded a space looks based on active check-ins.

    The current demo database has no active check-ins yet, so most spaces
    currently show as low usage. This function is ready for future check-in data.
    */

    // Small counts are treated as low usage.
    if (count <= 4) {
        return {
            label: "Low usage",
            className: "good",
            text: "This space looks lightly used based on the current check-in estimate."
        };
    }

    // Medium counts are treated as moderate usage.
    if (count <= 9) {
        return {
            label: "Moderate usage",
            className: "warning",
            text: "This space may still be usable, but people may need to share or rotate."
        };
    }

    // Larger counts are treated as high usage.
    return {
        label: "High usage",
        className: "danger",
        text: "This space may be crowded based on the current check-in estimate."
    };
}


function noiseDescription(noiseLevel) {
    /*
    Give a plain-English explanation of the estimated noise level.

    The backend database does not currently store noise_level, so the Flask app
    estimates it from the facility type before sending card data to this file.
    */

    if (noiseLevel === "Quiet") {
        return "Best for focused work, reading, or studying alone.";
    }

    if (noiseLevel === "Moderate") {
        return "Good for casual work, light conversation, or open recreation.";
    }

    if (noiseLevel === "Loud") {
        return "Better for social studying or groups that do not need a quiet environment.";
    }

    return "Noise level is estimated because this field is not stored in the current backend database yet.";
}


function formatScheduleItem(item) {
    /*
    Convert one schedule item into an HTML list item.

    This function supports both:
    1. Backend API schedule fields, such as day_of_week, start_time, and end_time.
    2. Older UI schedule fields, such as day and time.
    */

    // Use backend field names when available, otherwise use older UI names.
    const day = item.day_of_week || item.day || "Unknown day";

    // Use the schedule status if available.
    const status = item.status || "Unknown";

    // Use the schedule note if available.
    const note = item.note || "";

    // Start with a safe default in case time values are missing.
    let timeText = "Time unavailable";

    // Backend API format: start_time and end_time.
    if (item.start_time && item.end_time) {
        timeText = `${item.start_time} - ${item.end_time}`;
    }

    // Existing UI format: one combined time string.
    else if (item.time) {
        timeText = item.time;
    }

    // Add the note only if one exists.
    const noteText = note ? ` (${note})` : "";

    return `<li><strong>${day}:</strong> ${timeText} — ${status}${noteText}</li>`;
}


// ---------------------------------------------------------------------
// Filtering
// ---------------------------------------------------------------------

function filterCards() {
    /*
    Show or hide facility cards based on the selected filters.

    This does not call the backend. It filters the cards that Flask already
    loaded onto the page.
    */

    // Read the current filter values from the page.
    const searchText = searchInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value;
    const selectedType = typeFilter.value;
    const selectedNoise = noiseFilter.value;
    const selectedDay = dayFilter.value;

    // Check every card on the page.
    cards.forEach(card => {
        // Each card stores its facility data inside data-space as JSON.
        const space = JSON.parse(card.dataset.space);

        // Check whether the space name matches the search box.
        const nameMatches = space.name.toLowerCase().includes(searchText);

        // Check the category dropdown.
        const categoryMatches =
            selectedCategory === "all" || space.category === selectedCategory;

        // Check the facility type dropdown.
        const typeMatches =
            selectedType === "all" || space.facility_type === selectedType;

        // Check the noise level dropdown.
        const noiseMatches =
            selectedNoise === "all" || space.noise_level === selectedNoise;

        // Check whether the space has schedule information for the selected day.
        const dayMatches =
            selectedDay === "all" ||
            (space.schedule || []).some(item => item.day === selectedDay);

        // Only show the card if it passes every filter.
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


// ---------------------------------------------------------------------
// Backend API helper
// ---------------------------------------------------------------------

async function fetchJson(url, fallbackValue) {
    /*
    Request JSON data from the backend API.

    If the request fails, this function returns a fallback value instead of
    crashing the whole page. This keeps the UI usable even if one API route
    has missing data.
    */

    try {
        // Ask the backend for data.
        const response = await fetch(url);

        // If the backend returns an error, use the fallback value.
        if (!response.ok) {
            return fallbackValue;
        }

        // Convert the backend response into JavaScript data.
        return await response.json();
    } catch (error) {
        // Log the error for debugging, but keep the page running.
        console.error("API error:", url, error);
        return fallbackValue;
    }
}


// ---------------------------------------------------------------------
// Analysis panel
// ---------------------------------------------------------------------

async function showAnalysis(space) {
    /*
    Show detailed information for one selected facility.

    The card already has basic information. This function asks the backend API
    for the newest rules, hours, schedule, check-ins, and group-size guidance.
    */

    // Remember this selected space so the analysis can refresh later.
    selectedSpace = space;

    // Get the selected facility ID from the card data.
    const facilityId = space.facility_id;

    // Get the current group size from the number input.
    const groupSize = Number(groupSizeInput.value || 1);

    // Get the currently selected day from the day filter.
    const selectedDay = dayFilter.value;

    // Show a loading message while API requests are running.
    analysisPanel.innerHTML = `
        <p class="tag">Space Analysis</p>
        <h2>${space.name}</h2>
        <p>Loading backend data...</p>
    `;

    // Request rule information for this facility.
    const rules = await fetchJson(`/api/facilities/${facilityId}/rules`, null);

    // Build the schedule URL. If the user picked a day, request that day only.
    const scheduleUrl = selectedDay === "all"
        ? `/api/facilities/${facilityId}/schedule`
        : `/api/facilities/${facilityId}/schedule?day=${selectedDay}`;

    // Request schedule information from the backend.
    const schedule = await fetchJson(scheduleUrl, []);

    // Request facility hours from the backend.
    const hours = await fetchJson(`/api/facilities/${facilityId}/hours`, []);

    // Request check-ins from the backend.
    const checkins = await fetchJson(`/api/facilities/${facilityId}/checkins`, []);

    // Request group-size guidance from the backend.
    // Important: Kai's route expects "size", not "group_size".
    const groupCheck = await fetchJson(
        `/api/facilities/${facilityId}/check-group?size=${groupSize}`,
        null
    );

    // Keep only active check-ins.
    const activeCheckins = Array.isArray(checkins)
        ? checkins.filter(item => item.status === "active")
        : [];

    // Estimate current use by adding up the group sizes from active check-ins.
    const currentCount = activeCheckins.reduce((total, item) => {
        return total + Number(item.group_size || 0);
    }, 0);

    // Convert the usage count into a label, color class, and message.
    const usage = usageStatus(currentCount);

    // Decide whether the group-size box should be green or red.
    const groupClass =
        groupCheck && groupCheck.eligible === false ? "danger" : "good";

    // Build the group-size message from the backend response.
    const groupMessage = groupCheck
        ? groupCheck.eligible === false
            ? `${groupCheck.notes || ""} ${groupCheck.warning || ""}`
            : `Your group size is ${groupSize}. ${groupCheck.notes || "This group size appears to be within the listed limit."}`
        : "Group-size guidance is unavailable.";

    // Build the schedule list for the analysis panel.
    const scheduleHtml = Array.isArray(schedule) && schedule.length
        ? schedule.map(formatScheduleItem).join("")
        : "<li>No schedule data for this selected day.</li>";

    // Build the hours list for the analysis panel.
    const hoursHtml = Array.isArray(hours) && hours.length
        ? hours.map(item => `<li><strong>${item.day_of_week}:</strong> ${item.open_time} - ${item.close_time}</li>`).join("")
        : "<li>No hours listed for this facility.</li>";

    // Use backend rule values when available.
    // If something is missing, fall back to the card data.
    const costStatus = rules?.cost_status || space.cost_status || "Unknown";
    const costNotes = rules?.cost_notes || space.cost_notes || "No cost notes available.";
    const reservationType = rules?.reservation_type || space.reservation_type || "Unknown";
    const restrictions = rules?.restrictions || space.restrictions || "No restrictions listed.";
    const ruleNotes = rules?.rule_notes || space.rule_notes || "No rule notes available.";

    // Replace the loading message with the full analysis panel.
    analysisPanel.innerHTML = `
        <p class="tag">Space Analysis</p>
        <h2>${space.name}</h2>
        <p class="muted">${space.location} · ${space.category} · ${space.facility_type}</p>

        <div class="analysis-box ${usage.className}">
            <strong>${usage.label}</strong>
            <p>${usage.text}</p>
            <p><strong>Current active check-ins:</strong> ${currentCount}</p>
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
                <li><strong>Cost:</strong> ${costStatus}</li>
                <li><strong>Cost Notes:</strong> ${costNotes}</li>
                <li><strong>Use Type:</strong> ${reservationType}</li>
                <li><strong>Restrictions:</strong> ${restrictions}</li>
                <li><strong>Notes:</strong> ${ruleNotes}</li>
            </ul>
        </div>

        <div class="analysis-box">
            <strong>Hours</strong>
            <ul>${hoursHtml}</ul>
        </div>

        <div class="analysis-box">
            <strong>Schedule / Availability Notes</strong>
            <ul>${scheduleHtml}</ul>
            <p class="muted">This is demo schedule guidance, not live official availability.</p>
        </div>

        <div class="analysis-box">
            <strong>Next Step</strong>
            <p>${reservationType}. ${ruleNotes}</p>
        </div>

        <a href="/facility/${facilityId}">
            <button type="button">Open Facility Page</button>
        </a>
    `;
}


// ---------------------------------------------------------------------
// Group-size controls
// ---------------------------------------------------------------------

function updateGroupSize(amount) {
    /*
    Increase or decrease the group size input.

    If a facility is already selected, refresh the analysis panel so the
    group-size guidance updates immediately.
    */

    // Read the current group size.
    let current = Number(groupSizeInput.value || 1);

    // Add or subtract from the current value.
    current += amount;

    // Do not allow group size to go below 1.
    if (current < 1) {
        current = 1;
    }

    // Update the input on the page.
    groupSizeInput.value = current;

    // Refresh the selected facility analysis if one is open.
    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
}


// ---------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------

// Add click behavior to every "View Analysis" button.
cards.forEach(card => {
    const button = card.querySelector(".analysis-button");

    button.addEventListener("click", () => {
        // Read this card's facility data.
        const space = JSON.parse(card.dataset.space);

        // Show the full analysis for this facility.
        showAnalysis(space);
    });
});

// Update visible cards whenever the search box changes.
searchInput.addEventListener("input", filterCards);

// Update visible cards whenever the category filter changes.
categoryFilter.addEventListener("change", filterCards);

// Update visible cards whenever the type filter changes.
typeFilter.addEventListener("change", filterCards);

// Update visible cards whenever the noise filter changes.
noiseFilter.addEventListener("change", filterCards);

// Update visible cards and refresh analysis whenever the day filter changes.
dayFilter.addEventListener("change", () => {
    filterCards();

    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
});

// Refresh the analysis when the user types a new group size.
groupSizeInput.addEventListener("input", () => {
    // Do not allow group size below 1.
    if (Number(groupSizeInput.value) < 1) {
        groupSizeInput.value = 1;
    }

    // Refresh the analysis panel if a space is selected.
    if (selectedSpace) {
        showAnalysis(selectedSpace);
    }
});

// Decrease group size when the minus button is clicked.
decreaseGroup.addEventListener("click", () => updateGroupSize(-1));

// Increase group size when the plus button is clicked.
increaseGroup.addEventListener("click", () => updateGroupSize(1));