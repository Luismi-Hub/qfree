import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from quantfreedom.enums import CandleBodyType

from quantfreedom.helper_funcs import dl_ex_candles, cart_product

from quantfreedom.indicators.tv_indicators import macd_tv, ema_tv

from quantfreedom.strategies.strategy import Strategy

from logging import getLogger
from typing import NamedTuple

logger = getLogger("info")


class IndicatorSettingsArrays(NamedTuple):
    ema_length: np.array
    fast_length: np.array
    macd_below: np.array
    signal_smoothing: np.array
    slow_length: np.array

class MACDandEMA(Strategy):
    def __init__(
        self, 
        long_short: str, 
        ema_length: np.array,
        fast_length: np.array,
        macd_below: np.array, 
        signal_smoothing: np.array, 
        slow_length: np.array
    ):
        self.long_short = long_short
        self.log_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        cart_arrays = cart_product(
            named_tuple=IndicatorSettingsArrays(
                ema_length=ema_length,
                fast_length=fast_length,
                macd_below=macd_below,
                signal_smoothing=signal_smoothing,
                slow_length=slow_length,
            )   
        )
            
        cart_arrays = cart_arrays.T[cart_arrays[1] < cart_arrays[4]].T

        self.indicator_settings_arrays: IndicatorSettingsArrays = IndicatorSettingsArrays(
                ema_length=cart_arrays[0].astype(np.int_),
                fast_length=cart_arrays[1].astype(np.int_),
                macd_below=cart_arrays[2].astype(np.int_),
                signal_smoothing=cart_arrays[3].astype(np.int_),
                slow_length=cart_arrays[4].astype(np.int_),
            )

        if long_short == "long":
                self.set_entries_exits_array = self.long_set_entries_exits_array
                self.log_indicator_settings = self.long_log_indicator_settings
                self.entry_message = self.long_entry_message
                self.live_evalutate = self.long_live_evaluate
                self.chart_title = "Long Signal"
        else:
                self.set_entries_exits_array = self.short_set_entries_exits_array
                self.log_indicator_settings = self.short_log_indicator_settings
                self.entry_message = self.short_entry_message
                self.live_evalutate = self.short_live_evaluate
                self.chart_title = "Short Signal"


    def long_set_entries_exits_array(
             
        self, 
        candles: np.array, 
        ind_set_index: int,
              
    ):
        try:
             
            closing_prices = candles[:, CandleBodyType.Close]
            low_prices = candles[:, CandleBodyType.Low]

            self.ema_length = self.indicator_settings_arrays.ema_length[ind_set_index]
            self.fast_length = self.indicator_settings_arrays.fast_length[ind_set_index]
            self.macd_below = self.indicator_settings_arrays.macd_below[ind_set_index]
            self.signal_smoothing = self.indicator_settings_arrays.signal_smoothing[ind_set_index]
            self.slow_length = self.indicator_settings_arrays.slow_length[ind_set_index]

            self.histogram, self.macd, self.signal = macd_tv(
                source=closing_prices,
                fast_length=self.fast_length,
                slow_length=self.slow_length,
                signal_smoothing=self.signal_smoothing
            )

            self.ema = ema_tv(
                source=closing_prices,
                length=self.ema_length,
            )

            prev_macd = np.roll(self.macd, 1)
            prev_macd[0] = np.nan

            prev_signal = np.roll(self.signal, 1)
            prev_signal[0] = np.nan


            macd_below_signal = prev_macd < prev_signal
            macd_above_signal = self.macd > self.signal
            low_price_below_ema = low_prices > self.ema
            macd_below_number = self.macd < self.macd_below

            self.entries = (
                (low_price_below_ema == True)
                & (macd_below_signal == True)
                & (macd_above_signal == True)
                & (macd_below_number == True)
            )

            self.entry_signals = np.where(self.entries, self.macd, np.nan)

            self.exit_prices = np.full_like(self.entries, np.nan)

        except Exception as e:
            logger.error(f"Exception long_set_entries_exits_array ->{e}")
            raise Exception(f"Exception long_set_entries_exits_array ->{e}")
                    

    def long_log_indicator_settings(
            self,
            ind_set_index: int,
        ):
             
            logger.info(
                
                f"Indicator Settings:\
            \nIndicator Settings Index: {ind_set_index} \
            \nema Length: {self.ema_length} \
            \nfast Length: {self.fast_length} \
            \nmac Below: {self.macd_below} \
            \nsignal Smoothing: {self.signal_smoothing} \
            \nslow Length: {self.slow_length}"

            )

            

    def long_entry_message(
            self,
            bar_index: int,
        ):        
            logger.info("\n\n")
            logger.info(f"Entry time!!!")
         



         
         ##############   SHORTTTTTTT    #############

            
    def short_set_entries_exits_array(
            self,
            candles: np.array,
            ind_set_index: int,
        ):
            pass

    def short_log_indicator_settings(
            self,
            ind_set_index: int,
            
        ):
            pass

    def short_entry_message(
            self,
            bar_index: int,
       ): 
            pass
    
        ###### PLOTS #####################################################


    def plot_signals(

        self,
        candles:np.array
    ):

        fig = go.Figure()
        datetimes = candles[:, CandleBodyType.Timestamp].astype('datetime64[ms]')
        fig = make_subplots(
            cols=1,
            rows=2,                
            shared_xaxes=True,
            subplot_titles=["Candles","MACD"],
            row_heights=[0.6,0.4],
            vertical_spacing=0.1,
        )
             
        fig.append_trace(
            go.Candlestick(
                x=datetimes,
                open=candles[:, CandleBodyType.Open],
                high=candles[:, CandleBodyType.High],
                low=candles[:, CandleBodyType.Low],
                close=candles[:, CandleBodyType.Close],
                name="Candles",
                ),
                col=1,
                    row=1,
                )

        fig.append_trace(
                go.Scatter(
                    x=datetimes,
                    y=self.ema,
                    name="EMA",
                    line_color="yellow",
                ),

                col=1,
                row=1
            )

        ind_shift = np.roll(self.histogram, 1)
        ind_shift[0]=np.nan
        colors = np.where(
                self.histogram >= 0,
                np.where(ind_shift < self.histogram, "#26A69A", "#82DFD8"),
                np.where(ind_shift < self.histogram, "#FFCDD2", "#FF5252"),
            )
        fig.append_trace(
                go.Bar(
                    x=datetimes,
                    y=self.histogram,
                    name="histogram",
                    marker_color=colors,
                ),

                row=2,
                col=1
            )

        fig.append_trace(
                go.Scatter(
                    x=datetimes,
                    y=self.macd,
                    name="macd",
                    line_color="#2962FF"
                ),

                row=2,
                col=1
            )

        fig.append_trace(
                go.Scatter(
                    x=datetimes,
                    y=self.signal,
                    name="signal",
                    line_color="#FF6D00"
                ),

                row=2,
                col=1
            )
        fig.append_trace(
                go.Scatter(
                    x=datetimes,
                    y=self.entry_signals,
                    mode="markers",
                    name="entries",
                    marker=dict(
                        size=12,
                        symbol="circle",
                        color="#00F6FF",
                        line=dict(
                            width=1,
                            color="darkSlateGray"
                        )
                    )
                ),

                row=2,
                col=1
            )

        fig.update_layout(height=500,xaxis_rangeslider_visible=False)

        fig.show()
