import { notify } from 'components/Notifier/Notifier';

const defaultStyles = {
  success: { backgroundColor: 'green', color: 'white' },
  error: { backgroundColor: 'red', color: 'white' },
  warning: { backgroundColor: 'orange', color: 'white' },
  info: { backgroundColor: 'blue', color: 'white' },
};

export const showNotification = (message, type = 'info') => {
  const style = defaultStyles[type] || defaultStyles.info;

  notify(message, {
    style,
  });
};

export const notifySuccess = (message) => showNotification(message, 'success');
export const notifyError = (message) => showNotification(message, 'error');
export const notifyWarning = (message) => showNotification(message, 'warning');
export const notifyInfo = (message) => showNotification(message, 'info');
