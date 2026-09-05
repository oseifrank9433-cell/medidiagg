import { flushSync } from 'react-dom';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import VitalsPulse from './VitalsPulse';

const clinicianLinks = [
  { to: '/dashboard', label: 'Overview', icon: IconGrid },
  { to: '/diagnosis/new', label: 'New Screening', icon: IconPlus },
  { to: '/patients', label: 'Patient Records', icon: IconFolder },
  { to: '/profile', label: 'My Profile', icon: IconUser },
];

const adminLinks = [
  { to: '/admin/dashboard', label: 'Facility Overview', icon: IconGrid },
  { to: '/admin/settings', label: 'Facility Settings', icon: IconGear },
  { to: '/admin/profile', label: 'My Profile', icon: IconUser },
];

function IconGrid() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="1.5" y="1.5" width="6.5" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
      <rect x="10" y="1.5" width="6.5" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
      <rect x="1.5" y="10" width="6.5" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
      <rect x="10" y="10" width="6.5" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
function IconPlus() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="7.3" stroke="currentColor" strokeWidth="1.4" />
      <path d="M9 5.5V12.5M5.5 9H12.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconFolder() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path
        d="M1.8 4.6C1.8 3.9 2.4 3.3 3.1 3.3H6.7L8.1 4.9H14.9C15.6 4.9 16.2 5.5 16.2 6.2V13C16.2 13.7 15.6 14.3 14.9 14.3H3.1C2.4 14.3 1.8 13.7 1.8 13V4.6Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}
function IconUser() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="6" r="3" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2.8 15.5C3.6 12.4 6 10.8 9 10.8C12 10.8 14.4 12.4 15.2 15.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconGear() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="2.6" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M9 2.4v1.7M9 13.9v1.7M15.6 9h-1.7M4.1 9H2.4M13.5 4.5l-1.2 1.2M5.7 12.3l-1.2 1.2M13.5 13.5l-1.2-1.2M5.7 5.7 4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
function IconSun() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="3.6" stroke="currentColor" strokeWidth="1.4" />
      <path d="M9 1.6V3.4M9 14.6V16.4M16.4 9H14.6M3.4 9H1.6M14 4L12.7 5.3M5.3 12.7L4 14M14 14L12.7 12.7M5.3 5.3L4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconMoon() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18" fill="none">
      <path d="M15 10.2A6.6 6.6 0 1 1 7.8 3 5.2 5.2 0 0 0 15 10.2Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}
function IconLogout() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18" fill="none">
      <path d="M7 15.5H4a1.3 1.3 0 0 1-1.3-1.3V3.8A1.3 1.3 0 0 1 4 2.5h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.8 12.3 15.5 9l-3.7-3.3M15.5 9H6.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Sidebar() {
  const { clinician, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const isAdmin = clinician?.accountType === 'admin';
  const links = isAdmin ? adminLinks : clinicianLinks;

  function handleLogout() {
    // flushSync forces the clinician-state update (and the guard's own
    // redirect-to-/login it triggers) to fully commit before we navigate —
    // otherwise our navigate('/') races AdminRoute/ProtectedRoute's redirect
    // and can lose.
    flushSync(() => logout());
    navigate('/');
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <VitalsPulse className="sidebar__pulse" animated={false} />
        <div>
          <div className="sidebar__brand-name">MediDiag</div>
          {isAdmin && <div className="sidebar__brand-sub">Admin Console</div>}
        </div>
      </div>

      <p className="sidebar__section-label">Menu</p>
      <nav className="sidebar__nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar__link${isActive ? ' sidebar__link--active' : ''}`}
          >
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <button className="sidebar__logout sidebar__logout--top" onClick={handleLogout}><IconLogout /> Sign out</button>

      <button className="theme-toggle" onClick={toggleTheme} type="button">
        {theme === 'light' ? <IconMoon /> : <IconSun />}
        <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
      </button>

      <div className="sidebar__foot">
        <div className="sidebar__clinician">
          <div className="sidebar__avatar">{clinician?.name?.[0]?.toUpperCase() || 'C'}</div>
          <div>
            <div className="sidebar__clinician-name">{clinician?.name}</div>
            <div className="sidebar__clinician-role">
              {isAdmin ? 'Administrator' : clinician?.role} · {clinician?.facility}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}