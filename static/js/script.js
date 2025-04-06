let globalData = null;
let simplifiedView = false;
let currentDateIndex = 0;
let currentMatchdayData = null;
let dateGroups = [];

document.getElementById('simplifiedView').addEventListener('change', function() {
    simplifiedView = this.checked;
    
    // Toggle date-time display in comparison view
    const dateTimes = document.querySelectorAll('#comparisonDisplay .match-date-time');
    dateTimes.forEach(dt => {
        dt.style.display = simplifiedView ? 'none' : 'inline-block';
    });
    
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
    
    // Sort matchdays numerically
    data.sort((a, b) => {
        const numA = parseInt(a);
        const numB = parseInt(b);
        return numA - numB;
    }).forEach(matchday => {
        // Format matchday as "Matchday X"
        const formattedMatchday = `Matchday ${matchday}`;
        
        const label = document.createElement('label');
        label.className = 'matchday-checkbox';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = formattedMatchday;
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
    
    // Show loading state
    document.getElementById('dataDisplay').innerHTML = '<p>Loading data...</p>';
    if (document.getElementById('matchdayDisplay')) {
        document.getElementById('matchdayDisplay').textContent = 'Loading...';
    }
    
    // Add a timeout to detect if the request is hanging
    const timeoutId = setTimeout(() => {
        console.error('Request timeout after 30 seconds');
        document.getElementById('dataDisplay').innerHTML = '<p class="error">Request timed out. Please try again.</p>';
    }, 30000);
    
    fetch(`/get_data/${encodeURIComponent(league)}?season=${encodeURIComponent(season)}`)
        .then(response => {
            console.log('Response received:', response.status);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(result => {
            console.log('Data received:', result);
            
            if (!result) {
                throw new Error('Empty response received');
            }
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            if (!result.data) {
                throw new Error('No data field in response');
            }
            
            if (Object.keys(result.data).length === 0) {
                document.getElementById('dataDisplay').innerHTML = '<p class="error">No data available for this season</p>';
                if (document.getElementById('matchdayDisplay')) {
                    document.getElementById('matchdayDisplay').textContent = 'No matchday data available';
                }
                return;
            }
            
            globalData = result.data;
            console.log('Processed data:', globalData);
            
            try {
                displayData(result.data);
                populateMatchdayCheckboxes(Object.keys(result.data));
                initializeMatchdayAnalysis();
                if (typeof updateCurrentMatchday === 'function') {
                    updateCurrentMatchday();
                }
            } catch (error) {
                console.error('Error processing data:', error);
                document.getElementById('dataDisplay').innerHTML = `<p class="error">Error processing data: ${error.message}</p>`;
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Error loading data:', error);
            document.getElementById('dataDisplay').innerHTML = `<p class="error">Error loading data: ${error.message}</p>`;
            if (document.getElementById('matchdayDisplay')) {
                document.getElementById('matchdayDisplay').textContent = 'Error loading matchday data';
            }
        });
}

function formatMatch(match, isComparison) {
    console.log("Original match string for " + (isComparison ? "comparison" : "regular") + ":", match);
    
    // Extract date information using the new format
    const datePattern = /<<DATE_INFO:([^>]*)>>/;
    const dateMatch = match.match(datePattern);
    let dateTimeHtml = '';
    
    // Process date if found
    if (dateMatch && dateMatch[1]) {
        const dateInfo = dateMatch[1].replace('DATE_INFO:', '');
        // Split into date and time parts
        const parts = dateInfo.trim().split(' ');
        const datePart = parts[0];
        const timePart = parts.length > 1 ? parts[1] : "15:00";  // Default time if not provided
        
        // Create date-time HTML
        dateTimeHtml = `<strong class="match-date-time" style="color: #2c3e50; background-color: #f8f9fa; padding: 2px 5px; border-radius: 3px; margin-right: 5px; display: ${(isComparison && simplifiedView) ? 'none' : 'inline-block'}">${datePart} ${timePart}</strong>`;
    }
    
    // Remove the date pattern from the string
    let formattedMatch = match.replace(datePattern, '');
    
    // Remove any remaining weight-related brackets
    formattedMatch = formattedMatch.replace(/\[\d+\s+[\d,\s]+\]/g, '');
    
    // Add the date back with proper formatting
    formattedMatch = `${dateTimeHtml} ${formattedMatch.trim()}`;
    
    console.log("Formatted match string:", formattedMatch);
    
    if (isComparison && simplifiedView) {
        // For simplified view, only show the result letter (H, A, or D)
        // First split by the arrow to get the result part
        const parts = formattedMatch.split('=>');
        if (parts.length > 1) {
            // Extract just the result letter (H, A, or D) and remove any odds
            const resultPart = parts[1].trim();
            const resultMatch = resultPart.match(/^([HAD])/);
            if (resultMatch) {
                // Return with the date-time (hidden via CSS) and just the result letter
                return `${dateTimeHtml}${resultMatch[1]}`;
            }
            // If no match, return the result part without any brackets
            return resultPart.replace(/\[.*?\]/g, '').trim();
        }
    }
    
    return formattedMatch;
}

function createMatchdayHTML(matchday, data, isComparison = false) {
    const decodeHTML = (html) => {
        const txt = document.createElement('textarea');
        txt.innerHTML = html;
        return txt.value;
    };

    let html = `<div class="matchday ${isComparison ? 'comparison-matchday' : ''}">`;
    html += `<h3>${matchday}</h3>`;
    
    // Add matches
    data.matches.forEach(match => {
        html += `<div class="match">${formatMatch(match, isComparison)}</div>`;
    });
    
    // Add all summary information in one section
    html += `<div class="summary">`;
    if (data.timing && data.timing.length > 0) {
        html += `<p>Timing[${data.timing.join(', ')}]</p>`;
    }
    if (data.rounds) {
        html += `<p>${data.rounds}</p>`;
    }
    if (data.question && data.out) {
        html += `<p>Question[${data.question.join(', ')}]</p>`;
        html += `<p>Answer[${data.out.join(', ')}]</p>`;
    }
    html += `</div>`;
    
    html += '</div>';
    return html;
}

function displayData(data) {
    const container = document.getElementById('dataDisplay');
    container.innerHTML = '';
    
    // Sort matchdays by season and matchday number
    const sortedMatchdays = Object.keys(data.matchdays).sort((a, b) => {
        const [seasonA, mdA] = a.split('-');
        const [seasonB, mdB] = b.split('-');
        if (seasonA !== seasonB) return seasonB - seasonA;
        return parseInt(mdA) - parseInt(mdB);
    });
    
    // Create container for all matchdays
    const allMatchdaysContainer = document.createElement('div');
    allMatchdaysContainer.className = 'all-matchdays';
    
    // Process each matchday
    sortedMatchdays.forEach(matchdayKey => {
        const matchday = data.matchdays[matchdayKey];
        const matchdayContainer = document.createElement('div');
        matchdayContainer.className = 'matchday-container';
        
        // Create matchday header
        const header = document.createElement('h2');
        header.textContent = `Season ${matchday.season} - Matchday ${matchday.matchday}`;
        matchdayContainer.appendChild(header);
        
        // Create table for matches
        const table = document.createElement('table');
        table.className = 'matchday-table';
        
        // Create table header
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr>
                <th>Date</th>
                <th>Home Team (Pos/Pts) [G:S/C]</th>
                <th>Away Team (Pos/Pts) [G:S/C]</th>
                <th>Result</th>
                <th>Odds</th>
                <th>Round</th>
                <th>Previous Results</th>
            </tr>
        `;
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        // Process each match
        matchday.matches.forEach(match => {
            const row = document.createElement('tr');
            
            // Format previous results
            const homePrevResult = match.home_prev_result ? `${match.home_prev_result}${match.home_prev_loc}` : '-';
            const awayPrevResult = match.away_prev_result ? `${match.away_prev_result}${match.away_prev_loc}` : '-';
            
            row.innerHTML = `
                <td>${match.date}</td>
                <td>${match.home_team} (<span class="team-position">${match.home_position}</span>/<span class="team-points">${match.home_points}</span>) [<span class="team-goals">${match.home_goals_scored}/${match.home_goals_conceded}</span>]</td>
                <td>${match.away_team} (<span class="team-position">${match.away_position}</span>/<span class="team-points">${match.away_points}</span>) [<span class="team-goals">${match.away_goals_scored}/${match.away_goals_conceded}</span>]</td>
                <td class="result-${match.result.toLowerCase()}">${match.result}</td>
                <td>${match.odds.home.toFixed(2)}/${match.odds.draw.toFixed(2)}/${match.odds.away.toFixed(2)}</td>
                <td class="h-rnd">${match.h_rnd}</td>
                <td>${homePrevResult} | ${awayPrevResult}</td>
            `;
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        matchdayContainer.appendChild(table);
        
        // Create summary section
        const summary = document.createElement('div');
        summary.className = 'summary';
        summary.innerHTML = `
            <p>Timing: ${matchday.timing.join(', ')}</p>
            <p>${matchday.rounds}</p>
            <p>Question: ${matchday.question.join(', ')}</p>
            <p>Answer: ${matchday.out.join(', ')}</p>
        `;
        matchdayContainer.appendChild(summary);
        
        allMatchdaysContainer.appendChild(matchdayContainer);
    });
    
    container.appendChild(allMatchdaysContainer);
}

function displayComparison(selectedMatchdays) {
    console.log('Displaying comparison for:', selectedMatchdays);
    console.log('Global data:', globalData);
    
    const comparisonDisplay = document.getElementById('comparisonDisplay');
    comparisonDisplay.innerHTML = '';
    
    // Create a flex container for the comparison
    const flexContainer = document.createElement('div');
    flexContainer.className = 'comparison-container';
    
    selectedMatchdays.forEach(matchday => {
        // Extract the matchday number from the format "Matchday X"
        const matchdayNum = matchday.split(' ')[1];
        console.log('Processing matchday:', matchdayNum);
        
        if (globalData && globalData[matchdayNum]) {
            console.log('Found data for matchday:', matchdayNum);
            const matchdayData = globalData[matchdayNum];
            const matchdayHtml = createMatchdayHTML(matchday, matchdayData, true);
            flexContainer.innerHTML += matchdayHtml;
        } else {
            console.error('No data found for matchday:', matchdayNum);
        }
    });
    
    comparisonDisplay.appendChild(flexContainer);
    
    // Add dates to matches after rendering
    addDatesToMatches();
    
    // Remove any background colors
    removeMatchColors();
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
    
    // Format the games with our new approach
    const formattedGames = games.map(match => {
        const formatted = formatMatch(match, false);
        console.log("Analysis formatted match:", formatted);
        return `<li class="match-item">${formatted}</li>`;
    });
    
    // Create new section for current date
    const dateSection = document.createElement('div');
    dateSection.className = 'date-section';
    dateSection.innerHTML = `
        <h3>Date ${currentDateIndex + 1} of ${totalDates}</h3>
        <ul>
            ${formattedGames.join('')}
        </ul>
    `;
    
    // Append new section instead of replacing all content
    displayDiv.appendChild(dateSection);
}

// Add this function to display the current matchday in the UI
function updateCurrentMatchday() {
    const matchdayDisplay = document.getElementById('matchdayDisplay');
    if (!matchdayDisplay || !globalData) return;
    
    // Find the latest matchday with data
    const matchdays = Object.keys(globalData).sort((a, b) => {
        const numA = parseInt(a.split(' ')[1]);
        const numB = parseInt(b.split(' ')[1]);
        return numB - numA; // Sort in descending order
    });
    
    if (matchdays.length > 0) {
        const currentMatchday = matchdays[0];
        matchdayDisplay.textContent = currentMatchday;
    } else {
        matchdayDisplay.textContent = "No matchday data available";
    }
}

// Add this function to directly add dates to match items after page load
function addDatesToMatches() {
    console.log("Adding dates to matches");
    
    // Wait for DOM to be fully loaded
    setTimeout(() => {
        const matchItems = document.querySelectorAll('.match-item');
        console.log(`Found ${matchItems.length} match items`);
        
        matchItems.forEach((item, index) => {
            // Check if this item already has a date
            if (!item.querySelector('.match-date') && !item.innerHTML.includes('style="color: #2c3e50;')) {
                // Add a default date and time if none exists
                const today = new Date();
                const dateStr = today.toISOString().split('T')[0];
                const timeStr = today.toTimeString().split(' ')[0].substring(0, 5);  // Format: HH:MM
                
                const dateElement = document.createElement('strong');
                dateElement.style.color = '#2c3e50';
                dateElement.style.backgroundColor = '#f8f9fa';
                dateElement.style.padding = '2px 5px';
                dateElement.style.borderRadius = '3px';
                dateElement.style.marginRight = '5px';
                dateElement.textContent = `${dateStr} ${timeStr}`;  // No square brackets
                
                // Insert at the beginning of the item
                if (item.firstChild) {
                    item.insertBefore(dateElement, item.firstChild);
                } else {
                    item.appendChild(dateElement);
                }
                
                console.log(`Added date and time to match item ${index}`);
            }
        });
    }, 1000);
}

// Add this function to remove any background colors from match items
function removeMatchColors() {
    console.log("Removing match colors");
    
    // Wait for DOM to be fully loaded
    setTimeout(() => {
        // Remove background colors from all spans in match items
        const coloredSpans = document.querySelectorAll('.match-item span[style*="background-color"]');
        console.log(`Found ${coloredSpans.length} colored spans`);
        
        coloredSpans.forEach(span => {
            span.style.backgroundColor = 'transparent';
            console.log("Removed background color from span");
        });
    }, 1000);
}

// Add this function to ensure dates are visible in comparison view
function ensureComparisonDates() {
    console.log("Ensuring dates in comparison view");
    
    // Get all match items in comparison view
    const comparisonItems = document.querySelectorAll('#comparisonDisplay .match-item');
    console.log(`Found ${comparisonItems.length} comparison items`);
    
    comparisonItems.forEach((item, index) => {
        // Check if this item already has a date
        let dateTime = item.querySelector('.match-date-time');
        
        if (!dateTime) {
            // If no date-time element exists, create one
            console.log(`Adding missing date-time to comparison item ${index}`);
            const today = new Date();
            const dateStr = today.toISOString().split('T')[0];
            const timeStr = today.toTimeString().split(' ')[0].substring(0, 5);
            
            dateTime = document.createElement('strong');
            dateTime.className = 'match-date-time';
            dateTime.style.color = '#2c3e50';
            dateTime.style.backgroundColor = '#f8f9fa';
            dateTime.style.padding = '2px 5px';
            dateTime.style.borderRadius = '3px';
            dateTime.style.marginRight = '5px';
            dateTime.style.display = simplifiedView ? 'none' : 'inline-block';
            dateTime.textContent = `${dateStr} ${timeStr}`;
            
            // Insert at the beginning of the item
            if (item.firstChild) {
                item.insertBefore(dateTime, item.firstChild);
            } else {
                item.appendChild(dateTime);
            }
        } else {
            // Ensure existing date-time is visible if not in simplified view
            console.log(`Updating existing date-time visibility for item ${index}`);
            dateTime.style.display = simplifiedView ? 'none' : 'inline-block';
        }
    });
}

function displayMatchday(matchdayData) {
    const matchdayContainer = document.getElementById('matchdayContainer');
    matchdayContainer.innerHTML = '';
    
    // Create table
    const table = document.createElement('table');
    table.className = 'matchday-table';
    
    // Create table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Date</th>
            <th>Home Team</th>
            <th>Away Team</th>
            <th>Result</th>
            <th>Odds (H/D/A)</th>
            <th>Round</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    
    // Add each match as a row
    matchdayData.matches.forEach(match => {
        const row = document.createElement('tr');
        
        // Format odds
        const oddsStr = `[${match.odds.home.toFixed(2)}, ${match.odds.draw.toFixed(2)}, ${match.odds.away.toFixed(2)}]`;
        
        // Format result with color
        let resultClass = '';
        switch(match.result) {
            case 'H': resultClass = 'result-home'; break;
            case 'A': resultClass = 'result-away'; break;
            case 'D': resultClass = 'result-draw'; break;
        }
        
        row.innerHTML = `
            <td>${match.date}</td>
            <td>${match.home_team}</td>
            <td>${match.away_team}</td>
            <td class="${resultClass}">${match.result}</td>
            <td>${oddsStr}</td>
            <td class="h-rnd">${match.h_rnd}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    matchdayContainer.appendChild(table);
}