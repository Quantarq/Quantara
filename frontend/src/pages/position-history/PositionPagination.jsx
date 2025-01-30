import React from 'react';
import ArrowLeftIcon from '@/assets/icons/arrow-left.svg?react';
import ArrowRightIcon from '@/assets/icons/arrow-right.svg?react';
import './positionPagination.css';

export default function PositionPagination({
  currentPage,
  setCurrentPage,
  isPending,
  tableData,
  positionsOnPage,
}) {
  const totalItems = tableData?.total_count || 0;
  const totalPages = Math.ceil(totalItems / positionsOnPage);
  const range = (length, startIdx = 1) =>
    [...Array(length).keys()].map((i) => i + startIdx);

  const setPage = (page) => {
    if (isPending || page < 1 || page > totalPages) {
      return;
    }
    setCurrentPage(page);
  };

  return (
    <div className="position-pagination">
      <div
        className={`pagination-button button-prev ${
          currentPage === 1 ? 'disabled' : ''
        }`}
        onClick={() => setPage(currentPage - 1)}
      >
        <ArrowLeftIcon />
      </div>
      <div className="pagination-pages-container">
        {range(totalPages).map((page) => (
          <div
            className={`pagination-page-number ${
              currentPage === page ? 'page-selected' : ''
            }`}
            key={page}
            onClick={() => setPage(page)}
          >
            {page}
          </div>
        ))}
      </div>
      <div
        className={`pagination-button button-next ${
          currentPage === totalPages ? 'disabled' : ''
        }`}
        onClick={() => setPage(currentPage + 1)}
      >
        <ArrowRightIcon />
      </div>
    </div>
  );
}
