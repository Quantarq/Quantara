import React from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const notify = (message) => toast(message);

const Notifier = () => {
  return (
    <div>
      <ToastContainer />
    </div>
  );
};

export { Notifier, notify };
