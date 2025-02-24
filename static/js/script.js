let globalData = null;
let simplifiedView = false;
let currentDateIndex = 0;
let currentMatchdayData = null;
let dateGroups = [];

document.getElementById('simplifiedView').addEventListener('change', function() {
    simplifiedView = this.checked;
    updateComparison();
});

function updateComparison() {
    const selected = getSelectedMatchdays();
    if (selected.length >= 2 && selected.length <= 5) {
        displayComparison(selected);
    }
}

function getSelectedMatchdays() {
    const checkboxes = document.querySelectorAll('#matchdayCheckboxes input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function populateMatchdayCheckboxes(data) {
    const container = document.getElementById('matchdayCheckboxes');
    container.innerHTML = '';
    
    console.log('Populating checkboxes with data:', data);
    
    // Ensure consistent matchday formatting
    data.sort((a, b) => {
        const numA = parseInt(a.split(' ')[1]);
        const numB = parseInt(b.split(' ')[1]);
        return numA - numB;
    }).forEach(matchday => {
        // Ensure matchday format is exactly "Matchday X"
        const formattedMatchday = `Matchday ${parseInt(matchday.split(' ')[1])}`;
        
        const label = document.createElement('label');
        label.className = 'matchday-checkbox';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = formattedMatchday;  // Use formatted value
        checkbox.addEventListener('change', function() {
            const selected = getSelectedMatchdays();
            console.log('Selected matchdays:', selected);
            document.getElementById('compareBtn').disabled = selected.length < 2 || selected.length > 5;
            
            if (selected.length >= 2 && selected.length <= 5) {
                console.log('Triggering comparison with:', selected);
                displayComparison(selected);
            } else if (selected.length === 0 || selected.length === 1) {
                document.getElementById('comparisonDisplay').innerHTML = '';
            }
        });
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(formattedMatchday));
        container.appendChild(label);
    });
}

function selectLeague(league) {
    console.log('Selecting league:', league);
    
    // Clear previous data
    document.getElementById('dataDisplay').innerHTML = '';
    document.getElementById('matchdayCheckboxes').innerHTML = '';
    document.getElementById('comparisonDisplay').innerHTML = '';
    globalData = null;
    
    // Update active button state
    const buttons = document.querySelectorAll('#leagueSelector button');
    buttons.forEach(button => button.classList.remove('active'));
    const selectedButton = Array.from(buttons).find(button => button.textContent.trim() === league);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
    
    fetch(`/get_data/${encodeURIComponent(league)}`)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);
            if (data.error) {
                console.error('Server error:', data.error);
                document.getElementById('dataDisplay').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }
            
            // Store all data globally
            globalData = data.data;
            
            // Populate season dropdown if seasons exist
            if (data.seasons && data.seasons.length > 0) {
                console.log('Found seasons:', data.seasons);
                populateSeasonDropdown(data.seasons);
            } else {
                console.error('No seasons found in data');
                document.getElementById('dataDisplay').innerHTML = '<p class="error">No seasons found</p>';
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            document.getElementById('dataDisplay').innerHTML = '<p class="error">Error loading data</p>';
        });
}

function populateSeasonDropdown(seasons) {
    const seasonDropdown = document.getElementById('season');
    seasonDropdown.innerHTML = '<option value="">Select a season</option>';
    seasonDropdown.disabled = false;

    seasons.forEach(season => {
        const option = document.createElement('option');
        option.value = season;
        option.textContent = season;
        seasonDropdown.appendChild(option);
    });

    // Add event listener for season selection
    seasonDropdown.addEventListener('change', function() {
        const selectedSeason = this.value;
        if (selectedSeason) {
            displaySeasonData(selectedSeason);
        }
    });
}

function displaySeasonData(season) {
    const league = document.querySelector('#leagueSelector button.active').textContent.trim();
    
    console.log('Fetching data for league:', league, 'season:', season);
    
    fetch(`/get_data/${encodeURIComponent(league)}?season=${encodeURIComponent(season)}`)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(result => {
            console.log('Received data for season:', result);
            if (result.error) {
                console.error('Server error:', result.error);
                document.getElementById('dataDisplay').innerHTML = `<p class="error">${result.error}</p>`;
                return;
            }
            
            globalData = result.data;
            displayData(result.data);
            populateMatchdayCheckboxes(Object.keys(result.data));
            initializeMatchdayAnalysis();  // Initialize the analysis section
        })
        .catch(error => {
            console.error('Fetch error:', error);
            document.getElementById('dataDisplay').innerHTML = '<p class="error">Error loading data</p>';
        });
}

function formatMatch(match, isComparison) {
    if (isComparison && simplifiedView) {
        return match.split('=>')[1].trim();
    }
    return match;  // Return the match string without any escaping
}

function createMatchdayHTML(matchday, data, isComparison = false) {
    const matchdayData = data[matchday];
    const matches = matchdayData.matches;
    const summary = matchdayData.summary;
    
    const className = isComparison 
        ? `comparison-item${simplifiedView ? ' simplified' : ''}` 
        : 'matchday';
    
    // Create a temporary div to decode HTML entities
    const decodeHTML = (html) => {
        const txt = document.createElement('textarea');
        txt.innerHTML = html;
        return txt.value;
    };
    
    return `
        <div class="${className}">
            <h3>${matchday}</h3>
            <ul>
                ${matches.map(match => `<li class="match-item">${decodeHTML(match)}</li>`).join('')}
            </ul>
            <div class="summary">
                <p>Timing: [${summary.timing.join(', ')}]</p>
                <p>Question: [${summary.question.join(', ')}]</p>
                <p>Answer: [${summary.out.join(', ')}]</p>
            </div>
        </div>
    `;
}

function displayData(data) {
    const displayDiv = document.getElementById('dataDisplay');
    const sortedMatchdays = Object.keys(data).sort((a, b) => {
        const numA = parseInt(a.split(' ')[1]);
        const numB = parseInt(b.split(' ')[1]);
        return numA - numB;
    });
    
    let html = '';
    sortedMatchdays.forEach(matchday => {
        html += createMatchdayHTML(matchday, data, false);  // Always show full view
    });
    
    displayDiv.innerHTML = html;
}

function displayComparison(matchdays) {
    const comparisonDiv = document.getElementById('comparisonDisplay');
    
    console.log('Attempting comparison with matchdays:', matchdays);
    console.log('Global data available:', globalData !== null);
    
    if (!globalData) {
        console.error('No global data available for comparison');
        return;
    }

    console.log('Available matchdays in global data:', Object.keys(globalData));
    
    let html = '';
    matchdays.forEach(matchday => {
        console.log(`Processing matchday: ${matchday}`);
        // Ensure consistent matchday format
        const formattedMatchday = `Matchday ${parseInt(matchday.split(' ')[1])}`;
        
        if (globalData[formattedMatchday]) {
            console.log(`Found data for matchday: ${formattedMatchday}`);
            html += createMatchdayHTML(formattedMatchday, globalData, true);
        } else {
            console.error(`Matchday ${formattedMatchday} not found in global data. Available keys:`, Object.keys(globalData));
        }
    });
    
    if (html) {
        comparisonDiv.innerHTML = html;
    } else {
        console.error('No HTML generated for comparison');
        comparisonDiv.innerHTML = '<p class="error">No data available for selected matchdays</p>';
    }
}

function initializeMatchdayAnalysis() {
    const analysisSelect = document.getElementById('analysisMatchday');
    const nextDateBtn = document.getElementById('nextDateBtn');
    
    // Clear previous options
    analysisSelect.innerHTML = '<option value="">Select Matchday</option>';
    
    if (globalData) {
        // Add matchday options
        Object.keys(globalData)
            .sort((a, b) => {
                const numA = parseInt(a.split(' ')[1]);
                const numB = parseInt(b.split(' ')[1]);
                return numA - numB;
            })
            .forEach(matchday => {
                const option = document.createElement('option');
                option.value = matchday;
                option.textContent = matchday;
                analysisSelect.appendChild(option);
            });
    }
    
    // Add event listeners
    analysisSelect.addEventListener('change', function() {
        if (this.value) {
            currentDateIndex = 0;
            currentMatchdayData = globalData[this.value];
            groupMatchesByDate();
            // Clear previous display
            document.getElementById('analysisDisplay').innerHTML = '';
            // Show first date's games
            displayCurrentDateGames();
            nextDateBtn.disabled = dateGroups.length <= 1;
        } else {
            currentMatchdayData = null;
            dateGroups = [];
            document.getElementById('analysisDisplay').innerHTML = '';
            nextDateBtn.disabled = true;
        }
    });
    
    nextDateBtn.addEventListener('click', function() {
        if (currentDateIndex < dateGroups.length - 1) {
            currentDateIndex++;
            displayCurrentDateGames();
            this.disabled = currentDateIndex >= dateGroups.length - 1;
        }
    });
}

function groupMatchesByDate() {
    dateGroups = [];
    if (!currentMatchdayData) return;
    
    const matches = currentMatchdayData.matches;
    const timing = currentMatchdayData.summary.timing;
    
    let currentIndex = 0;
    timing.forEach(gamesCount => {
        dateGroups.push(matches.slice(currentIndex, currentIndex + gamesCount));
        currentIndex += gamesCount;
    });
}

function displayCurrentDateGames() {
    const displayDiv = document.getElementById('analysisDisplay');
    if (!dateGroups[currentDateIndex]) {
        return;
    }
    
    const games = dateGroups[currentDateIndex];
    const totalDates = dateGroups.length;
    
    // Create new section for current date
    const dateSection = document.createElement('div');
    dateSection.className = 'date-section';
    dateSection.innerHTML = `
        <h3>Date ${currentDateIndex + 1} of ${totalDates}</h3>
        <ul>
            ${games.map(match => `<li class="match-item">${match}</li>`).join('')}
        </ul>
    `;
    
    // Append new section instead of replacing all content
    displayDiv.appendChild(dateSection);
}