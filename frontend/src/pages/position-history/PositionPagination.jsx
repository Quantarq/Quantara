import React from 'react';
import { ReactComponent as ArrowLeftIcon } from '../../assets/icons/arrow-left.svg';
import { ReactComponent as ArrowRightIcon } from '../../assets/icons/arrow-right.svg';
import './positionPagination.css';

export default function PositionPagination({ currentPage, setCurrentPage, isPending, tableData, positionsOnPage }) {
  const pagesCount = (totalItems, itemsPerPage) => Math.ceil(totalItems / itemsPerPage);
  const range = (length, startIdx = 1) => [...Array(length).keys()].map(i => i + startIdx);
  
  const setPage = (page) => {
    if (isPending || page < 1 || page > pagesCount(tableData.length, positionsOnPage)) {
      return;
    }
    setCurrentPage(page);
  };

  return (
    <div className="position-pagination">
      <div
        className={`pagination-button button-prev ${currentPage == 1 ? "disabled" : ""}`}
        onClick={() => setPage(currentPage - 1)}
      >
        <ArrowLeftIcon />
      </div>
      <div className="pagination-pages-container">
        {!isPending && tableData ?
          range(pagesCount(tableData.length, positionsOnPage)).map((page) => (
            <div
              className={`pagination-page-number ${currentPage == page ? "page-selected" : ""}`}
              key={page}
              onClick={() => setPage(page)}
            >
              {page}
            </div>
          )) : null}
      </div>
      <div
        className={`pagination-button button-next ${(tableData && currentPage == pagesCount(tableData.length, positionsOnPage)) ? "disabled" : ""}`}
        onClick={() => setPage(currentPage + 1)}
      >
        <ArrowRightIcon />
      </div>
    </div>
  )
}
