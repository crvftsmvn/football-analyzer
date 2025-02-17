let globalData = null;
let simplifiedView = false;

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
    globalData = null;  // Reset global data when changing leagues
    
    // Fetch and display data for selected league
    fetch(`/get_data/${league}`)
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
            globalData = data;  // Store the data globally
            displayData(data);
            populateMatchdayCheckboxes(Object.keys(data));
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
    return match;
}

function createMatchdayHTML(matchday, data, isComparison = false) {
    const matchdayData = data[matchday];
    const matches = matchdayData.matches;
    const summary = matchdayData.summary;
    
    const className = isComparison 
        ? `comparison-item${simplifiedView ? ' simplified' : ''}` 
        : 'matchday';
    
    return `
        <div class="${className}">
            <h3>${matchday}</h3>
            <ul>
                ${matches.map(match => `<li>${formatMatch(match, isComparison).replace(/</g, '&lt;').replace(/>/g, '&gt;')}</li>`).join('')}
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