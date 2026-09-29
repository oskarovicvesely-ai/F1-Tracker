const seasonPill = document.getElementById('season-pill');
const currentRoundEl = document.getElementById('current-round');
const nextRaceEl = document.getElementById('next-race');
const leaderDriverEl = document.getElementById('leader-driver');
const raceCalendarEl = document.getElementById('race-calendar');
const completedRacesEl = document.getElementById('completed-races');
const driverStandingsEl = document.getElementById('driver-standings');
const constructorStandingsEl = document.getElementById('constructor-standings');

function formatDateShort(dateString) {
  return new Intl.DateTimeFormat('cs-CZ', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(dateString));
}

function formatCountdown(dateString, timeString = '12:00:00Z') {
  const target = new Date(`${dateString}T${timeString}`);
  const difference = target.getTime() - Date.now();

  if (difference <= 0) {
    return 'teď';
  }

  const totalHours = Math.floor(difference / (1000 * 60 * 60));
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;

  if (days > 0) {
    return `za ${days}d ${hours}h`;
  }

  return `za ${hours}h`;
}

function renderRaceCalendar(races) {
  raceCalendarEl.innerHTML = '';

  const upcomingRaces = races.filter((race) => new Date(`${race.date}T${race.time || '00:00:00Z'}`) >= new Date());
  const visibleRaces = upcomingRaces.length ? upcomingRaces : races;

  visibleRaces.forEach((race) => {
    const raceDate = new Date(`${race.date}T${race.time || '00:00:00Z'}`);
    const now = new Date();
    const isPast = raceDate < now;

    const card = document.createElement('article');
    card.className = 'race-card';

    const round = document.createElement('div');
    round.className = 'race-round';
    round.textContent = `R${race.round}`;

    const meta = document.createElement('div');
    meta.className = 'race-meta';
    meta.innerHTML = `
      <h4>${race.name}</h4>
      <p>${race.location || race.circuit || 'F1 závod'}</p>
      <span class="status-pill ${isPast ? 'past' : 'upcoming'}">${isPast ? 'Hotovo' : 'Příští'}</span>
    `;

    const dateWrap = document.createElement('div');
    dateWrap.className = 'race-date';
    dateWrap.innerHTML = `
      <span>${formatDateShort(race.date)}</span>
      <strong>${race.time ? race.time.slice(0, 5) : '—'}</strong>
    `;

    card.append(round, meta, dateWrap);
    raceCalendarEl.appendChild(card);
  });
}

function renderCompletedRaces(races) {
  completedRacesEl.innerHTML = '';

  const pastRaces = races.filter((race) => new Date(`${race.date}T${race.time || '00:00:00Z'}`) < new Date());

  if (!pastRaces.length) {
    completedRacesEl.innerHTML = '<p class="muted">Ještě nebyl žádný závod odjetý.</p>';
    return;
  }

  pastRaces
    .slice()
    .reverse()
    .forEach((race) => {
      const item = document.createElement('div');
      item.className = 'completed-race-item';
      item.innerHTML = `
        <span class="mini-round">R${race.round}</span>
        <div class="mini-race-info">
          <strong>${race.name}</strong>
          <span>${race.location}</span>
        </div>
        <span class="mini-date">${formatDateShort(race.date)}</span>
      `;
      completedRacesEl.appendChild(item);
    });
}

function renderDriverStandings(standings) {
  driverStandingsEl.innerHTML = '';

  standings.forEach((entry) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><span class="rank-badge">${entry.position}</span></td>
      <td><span class="driver-name">${entry.givenName} ${entry.familyName}</span></td>
      <td><span class="team-name">${entry.team}</span></td>
      <td>${entry.points}</td>
    `;

    driverStandingsEl.appendChild(row);
  });
}

function renderConstructorStandings(standings) {
  constructorStandingsEl.innerHTML = '';

  standings.forEach((entry) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><span class="rank-badge">${entry.position}</span></td>
      <td><span class="team-name">${entry.name}</span></td>
      <td>${entry.points}</td>
    `;

    constructorStandingsEl.appendChild(row);
  });
}

function findNextRace(races) {
  const now = new Date();
  const upcoming = races.find((race) => new Date(`${race.date}T${race.time || '00:00:00Z'}`) >= now);
  return upcoming || races[races.length - 1];
}

async function loadF1Data() {
  try {
    const response = await fetch('/api/f1-data', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const { season, races, driverStandings, constructorStandings } = data;
    const nextRace = findNextRace(races);
    const nextRaceName = nextRace.location || nextRace.name;

    seasonPill.textContent = `${season} F1 sezóna`;
    currentRoundEl.textContent = `${nextRace.round}`;
    nextRaceEl.innerHTML = `${nextRaceName}<span class="countdown-pill">${formatCountdown(nextRace.date, nextRace.time)}</span>`;
    leaderDriverEl.textContent = `${driverStandings[0].givenName} ${driverStandings[0].familyName}`;

    renderRaceCalendar(races);
    renderCompletedRaces(races);
    renderDriverStandings(driverStandings);
    renderConstructorStandings(constructorStandings);
  } catch (error) {
    console.error(error);
    seasonPill.textContent = 'Nepodařilo se načíst data';
    currentRoundEl.textContent = 'Chyba';
    nextRaceEl.textContent = 'Chyba';
    leaderDriverEl.textContent = 'Chyba';
    raceCalendarEl.innerHTML = '<p class="muted">Data se nepodařilo načíst. Zkus obnovit stránku později.</p>';
    driverStandingsEl.innerHTML = '<tr><td colspan="4">Chyba načtení</td></tr>';
    constructorStandingsEl.innerHTML = '<tr><td colspan="3">Chyba načtení</td></tr>';
  }
}

loadF1Data();
