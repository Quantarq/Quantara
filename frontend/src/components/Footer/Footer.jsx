import React from 'react';
import { Link } from 'react-router-dom';
import { ReactComponent as Logo } from 'assets/images/logo.svg';
import { ReactComponent as TwitterIcon } from 'assets/icons/twitter.svg';
import { ReactComponent as TelegramIcon } from 'assets/icons/telegram.svg';
import { ReactComponent as DiscordIcon } from 'assets/icons/discord.svg';
import './footer.css';

function Footer() {
  return (
    <footer className='footer-container p-3 mt-auto'>
      <div className='container'>
        <div className='footer-logo'>
          <Link to='/'>
            <Logo />
          </Link>
        </div>
        <div>
          <p className='follow-us-text'>Follow us on</p>
          <div className='footer-social-cards'>
            <div className='social-card'>
              <a
                href='https://twitter.com/yourprofile'
                target='_blank'
                rel='noopener noreferrer'
              >
                <TwitterIcon />
              </a>
              <div>
                <p>Twitter</p>
              </div>
            </div>
            <div className='social-card'>
              <a
                href='https://discord.com/yourprofile'
                target='_blank'
                rel='noopener noreferrer'
              >
                <DiscordIcon />
              </a>
              <div>
                <p>Discord</p>
              </div>
            </div>
            <div className='social-card'>
              <a
                href='https://t.me/yourprofile'
                target='_blank'
                rel='noopener noreferrer'
              >
                <TelegramIcon />
              </a>
              <div>
                <p>Telegram</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className='line-text-container'>
        <div className='footer-line' />
        <div className='footer-text'>©2024. Spotnet All Right Reserved.</div>
      </div>
    </footer>
  );
}

export default Footer;
