let globalData = null;
let simplifiedView = false;

document.getElementById('leagueSelect').addEventListener('change', function() {
    const selectedLeague = this.value;
    if (selectedLeague) {
        fetchData(selectedLeague);
    } else {
        document.getElementById('dataDisplay').innerHTML = '';
        document.getElementById('matchdayCheckboxes').innerHTML = '';
        document.getElementById('comparisonDisplay').innerHTML = '';
    }
});

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
    
    Object.keys(data).sort((a, b) => {
        const numA = parseInt(a.split(' ')[1]);
        const numB = parseInt(b.split(' ')[1]);
        return numA - numB;
    }).forEach(matchday => {
        const label = document.createElement('label');
        label.className = 'matchday-checkbox';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = matchday;
        checkbox.addEventListener('change', function() {
            const selected = getSelectedMatchdays();
            document.getElementById('compareBtn').disabled = selected.length < 2 || selected.length > 5;
            
            // If valid selection, update comparison immediately
            if (selected.length >= 2 && selected.length <= 5) {
                displayComparison(selected);
            } else if (selected.length === 0 || selected.length === 1) {
                document.getElementById('comparisonDisplay').innerHTML = '';
            }
        });
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(matchday));
        container.appendChild(label);
    });
}

function fetchData(league) {
    fetch(`/get_data/${league}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            globalData = data;
            displayData(data);
            populateMatchdayCheckboxes(data);
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('dataDisplay').innerHTML = 
                `<p style="color: red;">Error loading data: ${error.message}</p>`;
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
    let html = '';
    matchdays.forEach(matchday => {
        html += createMatchdayHTML(matchday, globalData, true);  // Show simplified view if enabled
    });
    comparisonDiv.innerHTML = html;
}