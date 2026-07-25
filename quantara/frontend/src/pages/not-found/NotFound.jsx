import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './NotFound.css';
import { logger } from '@/utils/logger';

/**
 * NotFound page displayed for undefined routes.
 *
 * Renders a friendly 404 message with a link back to the home page
 * so users have a clear path forward instead of seeing a blank page.
 */
const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    // Log the unknown route to make it easier to spot broken links
    // in the browser console. Only log in development to avoid noise
    // in production browser consoles.
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      logger.warn(`NotFound: no route matches ${location.pathname}`);
    }
  }, [location.pathname]);

  return (
    <div className="not-found-container">
      <div className="not-found-content">
        <h1 className="not-found-code">404</h1>
        <h2 className="not-found-title">Page Not Found</h2>
        <p className="not-found-message">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link to="/" className="not-found-home-link">
          Return to Home
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
