import { createFileRoute } from "@tanstack/react-router";
import { Slider } from "../ui/core/trade/slider";
import { Graph } from "../ui/core/trade/graph";
import '../ui/core/trade/trade.css';
import { PeriodPicker } from "../ui/core/trade/period-picker";
import { TradeView } from "../ui/core/trade/trade-view";

export const Route = createFileRoute("/trade")({
	component: RouteComponent,
});

function RouteComponent() {
	return (
		<div className="flex flex-col lg:flex-row h-full gap-[24px] mt-[28px]">
			<div className="collapse lg:visible bg-[#0C1219] h-0 lg:h-[633px] pt-[20px] pr-[12px] 
			rounded-tr-2xl flex flex-col justify-between text-xs text-[#97A0A6] font-medium">
				<ul>
					<li className="px-[16px] py-[12px]">Trade</li>
					<li className="px-[16px] py-[12px]">Pool</li>
					<li className="px-[16px] py-[12px] active
					 bg-[#12171E] rounded-tr-4xl rounded-br-4xl text-[#F1F7FF]
					 border-1 border-[#1C73E8]/14 border-l-0 
					 ">Multiplayer</li>
				</ul>
				<ul>
					<li className="px-[16px] py-[12px]">Settings</li>
					<li className="px-[16px] py-[12px]">Log Out</li>
				</ul>
			</div>
			<div className="w-full">
				<h1 className="font-extrabold text-3xl text-[#1A232A]">
					TRADE
				</h1>
				<p className="text-[#F1F7FF]">
					Trade with precision. Multiplier your gain.
				</p>

				<Graph></Graph>
			</div>

			<div className="w-full flex flex-col mr-[80px] items-center lg:items-end r">

				<PeriodPicker className=" mb-[28px]"></PeriodPicker>	
				<TradeView></TradeView>

				<form className="max-w-lg min-w-md block  border-1 border-[#17191B] rounded-xl p-[24px] h-fit mt-16">
					<div className="w-full">
						<label className="uppercase text-xs text-[#556571]">health factor level</label>
						<input type="number" className="rounded-full border-1 border-[#17191B] 
					block w-full h-[43px] mt-[6px] px-5 text-white"/>
					</div>

					<div className="w-full mt-[32px]">
						<label className="uppercase text-xs text-[#556571]">liquidation price</label>
						<input type="number" className="rounded-full border-1 border-[#17191B] 
					block w-full h-[43px] mt-[6px] px-5 text-white"/>
					</div>

					<div className="w-full mt-[32px]">
						<div className="justify-between flex">
							<label className="uppercase text-xs text-[#556571]">interest rate APY</label>
							<span className="text-xs text-[#E5E5E5]">
								Please fill this field <span className="text-red-500">*</span>
							</span>
						</div>
						<input type="number" className="rounded-full border-1 border-[#17191B] 
					block w-full h-[43px] mt-[6px] px-5 text-white" />
					</div>

					<div className="w-full mt-[32px]">
						<label className="uppercase text-xs text-[#556571]">Multiplier</label>
						<Slider className="mt-4"></Slider>
					</div>

					<button className="text-center w-full rounded-full bg-[#121519] h-[44px]
				 text-[#556571] mt-[32px] font-medium text-sm" type="submit">
						Trade
					</button>
				</form>
			</div>




		</div>
	);
}
