let cameraData = {};
let currentCam = null;
let currentType = null;
let currentView = 'dashboard'; // 'dashboard', 'dates', 'times'
let currentTimestamps = [];
let currentTimeIndex = -1;
let currentShowingDate = '';
let currentShowingHour = null;
let currentAvailableHours = [];
let currentAvailableDates = [];

async function fetchCameras() {
    const loading = document.getElementById('loading');
    
    try {
        const response = await fetch('/api/cameras');
        if (!response.ok) throw new Error('Failed to fetch camera data');
        
        cameraData = await response.json();
        renderCameras(cameraData);
    } catch (error) {
        console.error('Error:', error);
        loading.innerHTML = `<p style="color: var(--danger)">Error loading cameras. Please try again later.</p>`;
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function renderCameras(data) {
    const dashboard = document.getElementById('dashboard');
    const dateView = document.getElementById('date-view');
    const timeView = document.getElementById('time-view');
    const backBtn = document.getElementById('back-btn');
    const mainTitle = document.getElementById('main-title');
    const subTitle = document.getElementById('sub-title');

    currentView = 'dashboard';
    dashboard.innerHTML = '';
    dashboard.classList.remove('hidden');
    dateView.classList.add('hidden');
    timeView.classList.add('hidden');
    backBtn.classList.add('hidden');
    mainTitle.textContent = 'SecureCam';
    subTitle.textContent = 'Real-time status of your security system';

    const cameraNames = Object.keys(data).sort();

    if (cameraNames.length === 0) {
        dashboard.innerHTML = '<p class="subtitle" style="grid-column: 1/-1">No cameras found.</p>';
        return;
    }

    cameraNames.forEach(name => {
        const camData = data[name];
        const photoCount = camData.photos_count || 0;
        const videoCount = camData.videos_count || 0;

        const card = document.createElement('div');
        card.className = 'camera-card';
        card.innerHTML = `
            <h2>${name}</h2>
            <div class="stats">
                <div class="stat-item clickable" onclick="prepareDates('${name}', 'photos')">
                    <span class="stat-value">${photoCount}</span>
                    <span class="stat-label">Photos</span>
                </div>
                <div class="stat-item clickable" onclick="prepareDates('${name}', 'videos')">
                    <span class="stat-value">${videoCount}</span>
                    <span class="stat-label">Videos</span>
                </div>
            </div>
        `;
        
        dashboard.appendChild(card);
    });
}
async function prepareDates(camName, type) {
    // Check if we need to fetch full camera data
    if (!cameraData[camName].photos) {
        try {
            const response = await fetch(`/api/cameras/${camName}`);
            if (!response.ok) throw new Error('Failed to fetch camera details');
            const details = await response.json();
            cameraData[camName] = { ...cameraData[camName], ...details };
        } catch (error) {
            console.error('Error:', error);
            alert('Error loading camera details.');
            return;
        }
    }
    showDates(camName, type);
}

function showDates(camName, type) {
    currentCam = camName;
    currentType = type;
    currentView = 'dates';

    const dashboard = document.getElementById('dashboard');
    const dateView = document.getElementById('date-view');
    const timeView = document.getElementById('time-view');
    const datesGrid = document.getElementById('dates-grid');
    const backBtn = document.getElementById('back-btn');
    const mainTitle = document.getElementById('main-title');
    const subTitle = document.getElementById('sub-title');

    const files = cameraData[camName][type] || {};
    const timestamps = Object.keys(files);
    
    // Store ALL timestamps for this cam/type (Chronological)
    currentTimestamps = timestamps.sort();

    // Group by date (Newest first) for the dates list and count items
    const dateCounts = {};
    currentTimestamps.forEach(ts => {
        const date = new Date(parseInt(ts) * 1000).toISOString().split('T')[0];
        dateCounts[date] = (dateCounts[date] || 0) + 1;
    });

    currentAvailableDates = Object.keys(dateCounts).sort().reverse();
    const uniqueDates = currentAvailableDates;

    const toggleBtn = document.getElementById('date-view-toggle');
    toggleBtn.textContent = `Switch to ${type === 'photos' ? 'Videos' : 'Photos'}`;

    mainTitle.textContent = `${camName}`;
    subTitle.textContent = `Available ${type} by date`;
    
    dashboard.classList.add('hidden');
    dateView.classList.remove('hidden');
    timeView.classList.add('hidden');
    backBtn.classList.remove('hidden');
    document.getElementById('home-btn').classList.remove('hidden');

    datesGrid.innerHTML = '';
    
    if (uniqueDates.length === 0) {
        datesGrid.innerHTML = `<p class="subtitle">No ${type} found for this camera.</p>`;
        return;
    }

    uniqueDates.forEach(date => {
        const count = dateCounts[date];
        const dateCard = document.createElement('div');
        dateCard.className = 'date-card';
        dateCard.innerHTML = `
            <div style="font-size: 1.1rem; font-weight: 600">${date}</div>
            <div style="color: var(--accent-color); font-size: 0.9rem; margin-top: 0.25rem">${count} ${type}</div>
        `;
        dateCard.onclick = () => showTimes(camName, type, date);
        datesGrid.appendChild(dateCard);
    });
}

function showTimes(camName, type, dateString) {
    currentView = 'times';
    currentShowingDate = dateString;
    currentShowingHour = null;

    const dateView = document.getElementById('date-view');
    const timeView = document.getElementById('time-view');
    const timesGrid = document.getElementById('times-grid');
    const mainTitle = document.getElementById('main-title');
    const subTitle = document.getElementById('sub-title');

    // Filter the global currentTimestamps just for this date's list view
    const dateTimes = currentTimestamps.filter(ts => {
        const date = new Date(parseInt(ts) * 1000);
        return date.toISOString().split('T')[0] === dateString;
    });

    mainTitle.textContent = `${camName} - ${dateString}`;
    
    dateView.classList.add('hidden');
    timeView.classList.remove('hidden');
    document.getElementById('home-btn').classList.remove('hidden');
    document.getElementById('hour-navigation').classList.add('hidden');
    
    // Setup daily nav
    const dayNav = document.getElementById('day-navigation');
    const prevDayBtn = document.getElementById('prev-day-btn');
    const nextDayBtn = document.getElementById('next-day-btn');
    
    dayNav.classList.remove('hidden');
    const dateIndex = currentAvailableDates.indexOf(dateString);
    
    const hasPrevDay = dateIndex < currentAvailableDates.length - 1;
    const hasNextDay = dateIndex > 0;
    
    prevDayBtn.classList.toggle('hidden', !hasPrevDay);
    nextDayBtn.classList.toggle('hidden', !hasNextDay);
    prevDayBtn.disabled = !hasPrevDay;
    nextDayBtn.disabled = !hasNextDay;

    timesGrid.innerHTML = '';

    if (dateTimes.length > 24) {
        subTitle.textContent = `High activity: ${dateTimes.length} ${type} grouped by hour`;
        
        // Group by hour
        const hourMap = {};
        dateTimes.forEach(ts => {
            const date = new Date(parseInt(ts) * 1000);
            const hour = date.getHours().toString().padStart(2, '0');
            if (!hourMap[hour]) hourMap[hour] = 0;
            hourMap[hour]++;
        });

        // Sorted hours
        currentAvailableHours = Object.keys(hourMap).sort();
        
        currentAvailableHours.forEach(hour => {
            const hourCard = document.createElement('div');
            hourCard.className = 'date-card';
            hourCard.innerHTML = `
                <div style="font-size: 1.2rem; font-weight: 700">${hour}:00 - ${hour}:59</div>
                <div style="color: var(--accent-color); font-size: 0.9rem">${hourMap[hour]} items</div>
            `;
            hourCard.onclick = () => showHourTimes(camName, type, dateString, hour);
            timesGrid.appendChild(hourCard);
        });
    } else {
        subTitle.textContent = `Recorded ${type} times`;
        
        dateTimes.forEach((ts) => {
            const date = new Date(parseInt(ts) * 1000);
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
            
            const timeCard = document.createElement('div');
            timeCard.className = 'date-card'; 
            timeCard.innerHTML = `<span>${timeStr}</span>`;
            timeCard.onclick = () => {
                currentTimeIndex = currentTimestamps.indexOf(ts);
                viewMedia();
            };
            timesGrid.appendChild(timeCard);
        });
    }
}

function showHourTimes(camName, type, dateString, hour) {
    currentView = 'hour';
    currentShowingDate = dateString;
    currentShowingHour = hour;

    const timesGrid = document.getElementById('times-grid');
    const mainTitle = document.getElementById('main-title');
    const subTitle = document.getElementById('sub-title');
    const hourNav = document.getElementById('hour-navigation');

    mainTitle.textContent = `${camName} - ${dateString}`;
    const prevBtn = document.getElementById('prev-hour-btn');
    const nextBtn = document.getElementById('next-hour-btn');

    // Filter by date AND hour
    const hourTimes = currentTimestamps.filter(ts => {
        const date = new Date(parseInt(ts) * 1000);
        const dStr = date.toISOString().split('T')[0];
        const hStr = date.getHours().toString().padStart(2, '0');
        return dStr === dateString && hStr === hour;
    });

    subTitle.textContent = `Recordings between ${hour}:00 and ${hour}:59`;
    timesGrid.innerHTML = '';
    
    // Setup hourly nav
    document.getElementById('day-navigation').classList.add('hidden');
    hourNav.classList.remove('hidden');
    const hourIndex = currentAvailableHours.indexOf(hour);
    const dateIndex = currentAvailableDates.indexOf(dateString);
    
    const hasPrev = hourIndex > 0 || dateIndex < currentAvailableDates.length - 1;
    const hasNext = hourIndex < currentAvailableHours.length - 1 || dateIndex > 0;

    prevBtn.classList.toggle('hidden', !hasPrev);
    nextBtn.classList.toggle('hidden', !hasNext);
    
    prevBtn.disabled = !hasPrev;
    nextBtn.disabled = !hasNext;

    hourTimes.forEach((ts) => {
        const date = new Date(parseInt(ts) * 1000);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        
        const timeCard = document.createElement('div');
        timeCard.className = 'date-card'; 
        timeCard.innerHTML = `<span>${timeStr}</span>`;
        timeCard.onclick = () => {
            currentTimeIndex = currentTimestamps.indexOf(ts);
            viewMedia();
        };
        timesGrid.appendChild(timeCard);
    });
}

function nextHour() {
    const currentIndex = currentAvailableHours.indexOf(currentShowingHour);
    if (currentIndex < currentAvailableHours.length - 1) {
        showHourTimes(currentCam, currentType, currentShowingDate, currentAvailableHours[currentIndex + 1]);
    } else {
        // Try jumping to next day (Newer dates are at the start of currentAvailableDates)
        const dateIndex = currentAvailableDates.indexOf(currentShowingDate);
        if (dateIndex > 0) {
            const nextDay = currentAvailableDates[dateIndex - 1];
            // We need to re-group the next day to find its first hour
            const dayTimes = currentTimestamps.filter(ts => {
                const date = new Date(parseInt(ts) * 1000);
                return date.toISOString().split('T')[0] === nextDay;
            });
            const hours = [...new Set(dayTimes.map(ts => new Date(parseInt(ts) * 1000).getHours().toString().padStart(2, '0')))].sort();
            currentShowingDate = nextDay;
            currentAvailableHours = hours;
            showHourTimes(currentCam, currentType, nextDay, hours[0]);
        }
    }
}

function prevHour() {
    const currentIndex = currentAvailableHours.indexOf(currentShowingHour);
    if (currentIndex > 0) {
        showHourTimes(currentCam, currentType, currentShowingDate, currentAvailableHours[currentIndex - 1]);
    } else {
        // Try jumping to previous day (Older dates are at the end of currentAvailableDates)
        const dateIndex = currentAvailableDates.indexOf(currentShowingDate);
        if (dateIndex < currentAvailableDates.length - 1) {
            const prevDayStr = currentAvailableDates[dateIndex + 1];
            // We need to re-group the prev day to find its last hour
            const dayTimes = currentTimestamps.filter(ts => {
                const date = new Date(parseInt(ts) * 1000);
                return date.toISOString().split('T')[0] === prevDayStr;
            });
            const hours = [...new Set(dayTimes.map(ts => new Date(parseInt(ts) * 1000).getHours().toString().padStart(2, '0')))].sort();
            currentShowingDate = prevDayStr;
            currentAvailableHours = hours;
            showHourTimes(currentCam, currentType, prevDayStr, hours[hours.length - 1]);
        }
    }
}

function nextDay() {
    const dateIndex = currentAvailableDates.indexOf(currentShowingDate);
    if (dateIndex > 0) {
        showTimes(currentCam, currentType, currentAvailableDates[dateIndex - 1]);
    }
}

function prevDay() {
    const dateIndex = currentAvailableDates.indexOf(currentShowingDate);
    if (dateIndex < currentAvailableDates.length - 1) {
        showTimes(currentCam, currentType, currentAvailableDates[dateIndex + 1]);
    }
}

function viewMedia() {
    const modal = document.getElementById('media-modal');
    const container = document.getElementById('media-container');
    const title = document.getElementById('modal-title');
    const details = document.getElementById('modal-details');
    const download = document.getElementById('modal-download');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const switchBtn = document.getElementById('switch-btn');
    const cameraSelect = document.getElementById('camera-select');

    const ts = currentTimestamps[currentTimeIndex];
    const files = cameraData[currentCam][currentType];
    const relPath = files[ts];
    
    const date = new Date(parseInt(ts) * 1000);
    const dateStr = date.toISOString().split('T')[0];
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

    const fileUrl = `/data/${currentCam}/${relPath}`;
    const videoUrl = relPath.toLowerCase().endsWith('.mkv') ? `/video/${currentCam}/${relPath}` : fileUrl;
    
    container.innerHTML = '';
    if (currentType === 'photos') {
        const img = document.createElement('img');
        img.src = fileUrl;
        img.alt = `${currentCam} photo at ${timeStr}`;
        container.appendChild(img);
    } else {
        const video = document.createElement('video');
        video.src = videoUrl;
        video.controls = true;
        video.autoplay = true;
        container.appendChild(video);
    }

    title.textContent = `${currentCam} - ${currentType === 'photos' ? 'Photo' : 'Video'}`;
    details.textContent = `${dateStr} at ${timeStr}`;
    download.href = fileUrl;
    download.download = relPath.split('/').pop();

    // Populate camera dropdown
    cameraSelect.innerHTML = '';
    Object.keys(cameraData).sort().forEach(cam => {
        const option = document.createElement('option');
        option.value = cam;
        option.textContent = cam;
        option.selected = (cam === currentCam);
        cameraSelect.appendChild(option);
    });

    // Switch button visibility and text
    const otherType = currentType === 'photos' ? 'videos' : 'photos';
    const otherFiles = cameraData[currentCam][otherType] || {};
    
    if (Object.keys(otherFiles).length > 0) {
        switchBtn.classList.remove('hidden');
        switchBtn.textContent = `Switch to ${otherType === 'photos' ? 'Photos' : 'Videos'}`;
    } else {
        switchBtn.classList.add('hidden');
    }

    // Button states
    prevBtn.disabled = currentTimeIndex <= 0;
    nextBtn.disabled = currentTimeIndex >= currentTimestamps.length - 1;
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; 

    // Prefetch next and previous
    if (currentTimeIndex < currentTimestamps.length - 1) {
        const nextTs = currentTimestamps[currentTimeIndex + 1];
        const nextPath = cameraData[currentCam][currentType][nextTs];
        const nextUrl = nextPath.toLowerCase().endsWith('.mkv') ? `/video/${currentCam}/${nextPath}` : `/data/${currentCam}/${nextPath}`;
        if (currentType === 'photos') {
            new Image().src = nextUrl;
        } else {
            const v = document.createElement('video');
            v.src = nextUrl;
            v.preload = 'auto';
        }
    }
}

function toggleMediaType() {
    const newType = currentType === 'photos' ? 'videos' : 'photos';
    prepareDates(currentCam, newType);
}

async function switchCamera(newCamName) {
    if (newCamName === currentCam) return;

    // Ensure we have data for the new camera
    if (!cameraData[newCamName].photos) {
        try {
            const response = await fetch(`/api/cameras/${newCamName}`);
            if (!response.ok) throw new Error('Failed to fetch camera details');
            const details = await response.json();
            cameraData[newCamName] = { ...cameraData[newCamName], ...details };
        } catch (error) {
            console.error('Error:', error);
            alert(`Error loading data for ${newCamName}`);
            document.getElementById('camera-select').value = currentCam;
            return;
        }
    }

    const ts = parseInt(currentTimestamps[currentTimeIndex]);
    const files = cameraData[newCamName][currentType] || {};
    const timestamps = Object.keys(files).map(t => parseInt(t)).sort((a, b) => a - b);
    
    if (timestamps.length === 0) {
        alert(`No ${currentType} found for ${newCamName}`);
        document.getElementById('camera-select').value = currentCam;
        return;
    }

    // Find nearest timestamp
    let nearestTs = timestamps[0];
    let minDiff = Math.abs(ts - nearestTs);

    for (let i = 1; i < timestamps.length; i++) {
        const diff = Math.abs(ts - timestamps[i]);
        if (diff < minDiff) {
            minDiff = diff;
            nearestTs = timestamps[i];
        } else if (diff > minDiff) {
            break;
        }
    }

    // Update state
    currentCam = newCamName;
    currentTimestamps = timestamps.map(t => t.toString());
    currentTimeIndex = currentTimestamps.indexOf(nearestTs.toString());
    
    viewMedia();
}

function switchToNearest() {
    const ts = parseInt(currentTimestamps[currentTimeIndex]);
    const otherType = currentType === 'photos' ? 'videos' : 'photos';
    const otherFiles = cameraData[currentCam][otherType] || {};
    const otherTimestamps = Object.keys(otherFiles).map(t => parseInt(t)).sort((a, b) => a - b);
    
    if (otherTimestamps.length === 0) return;

    // Find nearest timestamp
    let nearestTs = otherTimestamps[0];
    let minDiff = Math.abs(ts - nearestTs);

    for (let i = 1; i < otherTimestamps.length; i++) {
        const diff = Math.abs(ts - otherTimestamps[i]);
        if (diff < minDiff) {
            minDiff = diff;
            nearestTs = otherTimestamps[i];
        } else if (diff > minDiff) {
            // Since it's sorted, we can stop if diff starts increasing
            break;
        }
    }

    // Update state
    currentType = otherType;
    currentTimestamps = otherTimestamps.map(t => t.toString());
    currentTimeIndex = currentTimestamps.indexOf(nearestTs.toString());
    
    viewMedia();
}

function nextMedia() {
    if (currentTimeIndex < currentTimestamps.length - 1) {
        currentTimeIndex++;
        viewMedia();
    }
}

function goHome() {
    currentCam = '';
    currentType = '';
    currentTimestamps = [];
    currentTimeIndex = -1;
    currentShowingDate = '';
    currentShowingHour = null;
    currentView = 'dashboard';

    document.getElementById('date-view').classList.add('hidden');
    document.getElementById('time-view').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('back-btn').classList.add('hidden');
    document.getElementById('home-btn').classList.add('hidden');
    document.getElementById('day-navigation').classList.add('hidden');
    document.getElementById('hour-navigation').classList.add('hidden');
    
    document.getElementById('main-title').textContent = 'SecureCam';
    document.getElementById('sub-title').textContent = 'Real-time status of your security system';
}

function closeModal() {
    const modal = document.getElementById('media-modal');
    const container = document.getElementById('media-container');
    
    const video = container.querySelector('video');
    if (video) video.pause();
    
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function goBack() {
    if (currentView === 'hour') {
        showTimes(currentCam, currentType, currentShowingDate);
    } else if (currentView === 'times') {
        showDates(currentCam, currentType);
    } else {
        renderCameras(cameraData);
    }
}

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
    fetchCameras();
    document.getElementById('back-btn').addEventListener('click', goBack);
    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (document.getElementById('media-modal').classList.contains('hidden')) return;
        
        if (e.key === 'ArrowRight') nextMedia();
        if (e.key === 'ArrowLeft') prevMedia();
        if (e.key === 'Escape') closeModal();
    });
});
