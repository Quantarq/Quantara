import React from 'react';

const Spinner = ({ loading }) => {
  return (
    loading && (
      <div className="fixed top-0 left-0 w-full h-full flex justify-center items-center bg-spinner-bgn z-50">
        <div className="flex justify-center items-center rounded-xl py-3 px-8 w-3xs h-16 bg-spinner-content">
          <div className="h-9 w-9 mr-3" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <span className="font-semibold text-3xl text-primary">Loading...</span>
        </div>
      </div>
    )
  );
};

export default Spinner;
