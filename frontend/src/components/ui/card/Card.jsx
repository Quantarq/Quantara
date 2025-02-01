function Card({ label, icon, value = '', cardData = [] }) {
  return (
    <div className="flex flex-col   grow justify-center items-center text-center border-1 border-light-purple rounded-lg p-4 lg:w-[317px] h-[101px] sm:w-full sm:h-[90px] xs:h-auto bg-transparent">
      {/* Card Header */}
      <div className="flex items-center justify-center mb-2">
        {icon}
        <span className="text-sm font-semibold sm:font-normal text-gray ml-2">{label}</span>
      </div>

      {/* Card Value */}
      <div className=" text-xl font-semibold sm:text-lg xs:text-base">
        {cardData.length > 0 ? (
          <>
            <span className="text-gray-500 mr-1 text-lg xs:text-sm">$</span>
            <span>{cardData[1]?.balance ? Number(cardData[1].balance).toFixed(8) : '0.00'}</span>
          </>
        ) : (
          <span>{value}</span>
        )}
      </div>
    </div>
  );
}

export default Card;
