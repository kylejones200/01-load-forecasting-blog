"""
Power System Analysis Service
Implements comprehensive power system analysis for load forecasting
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class PowerSystemService:
    """Service for power system analysis and electrical engineering calculations."""

    def __init__(self):
        """Initialize power system service."""
        self.system_parameters = {
        'base_mva': 100,
        'base_kv': 138,
        'frequency': 60.0,
        'voltage_tolerance': 0.05 # ±5%
        }

    def analyze_system_stability(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze power system stability for load forecast.

        Args:
        load_forecast: Forecasted load data
        system_data: System configuration and parameters

        Returns:
        Stability analysis results
        """
        try:
            # Calculate system inertia
            inertia_analysis = self._calculate_system_inertia(system_data)

            # Calculate frequency response
            frequency_response = self._calculate_frequency_response(load_forecast, system_data)

            # Calculate voltage stability
            voltage_stability = self._calculate_voltage_stability(load_forecast, system_data)

            # Calculate transient stability
            transient_stability = self._calculate_transient_stability(load_forecast, system_data)

            # Calculate small signal stability
            small_signal_stability = self._calculate_small_signal_stability(system_data)

            return {
            'inertia_analysis': inertia_analysis,
            'frequency_response': frequency_response,
            'voltage_stability': voltage_stability,
            'transient_stability': transient_stability,
            'small_signal_stability': small_signal_stability,
            'overall_stability_margin': self._calculate_overall_stability_margin(
            inertia_analysis, frequency_response, voltage_stability
            ),
            'stability_recommendations': self._generate_stability_recommendations(
            inertia_analysis, frequency_response, voltage_stability
            )
            }

        except Exception as e:
            return {'error': f'Stability analysis failed: {str(e)}'}

    def _calculate_system_inertia(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate system inertia and inertia constant."""
        # Simulate generator data
        generators = system_data.get('generators', [])
        if not generators:
            # Default generator data
            generators = [
            {'capacity': 500, 'inertia_constant': 4.0, 'type': 'thermal'},
            {'capacity': 300, 'inertia_constant': 3.5, 'type': 'thermal'},
            {'capacity': 200, 'inertia_constant': 2.0, 'type': 'renewable'}
            ]

            total_capacity = sum(gen['capacity'] for gen in generators)
            weighted_inertia = sum(gen['capacity'] * gen['inertia_constant'] for gen in generators)
            system_inertia_constant = weighted_inertia / total_capacity

            return {
            'system_inertia_constant': system_inertia_constant,
            'total_capacity': total_capacity,
            'inertia_by_type': self._calculate_inertia_by_type(generators),
            'inertia_adequacy': 'adequate' if system_inertia_constant > 3.0 else 'marginal'
            }

    def _calculate_inertia_by_type(self, generators: List[Dict]) -> Dict[str, Any]:
        """Calculate inertia by generator type."""
        inertia_by_type = {}
        for gen in generators:
            gen_type = gen['type']
            if gen_type not in inertia_by_type:
                inertia_by_type[gen_type] = {'capacity': 0, 'inertia': 0}
                inertia_by_type[gen_type]['capacity'] += gen['capacity']
                inertia_by_type[gen_type]['inertia'] += gen['capacity'] * gen['inertia_constant']

                # Calculate weighted averages
                for gen_type in inertia_by_type:
                    if inertia_by_type[gen_type]['capacity'] > 0:
                        inertia_by_type[gen_type]['weighted_inertia'] = (
                        inertia_by_type[gen_type]['inertia'] / inertia_by_type[gen_type]['capacity']
                        )

                        return inertia_by_type

    def _calculate_frequency_response(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate frequency response characteristics."""
        # Calculate load ramping rates
        load_ramping = load_forecast['consumption'].diff().abs()
        max_ramping_rate = load_ramping.max()
        avg_ramping_rate = load_ramping.mean()

        # Calculate frequency response requirements
        system_inertia = self._calculate_system_inertia(system_data)
        inertia_constant = system_inertia['system_inertia_constant']

        # Calculate frequency deviation for load changes
        frequency_deviations = []
        for ramping_rate in load_ramping.dropna():
            freq_deviation = self._calculate_frequency_deviation(ramping_rate, inertia_constant)
            frequency_deviations.append(freq_deviation)

            return {
            'max_ramping_rate': max_ramping_rate,
            'avg_ramping_rate': avg_ramping_rate,
            'max_frequency_deviation': max(frequency_deviations) if frequency_deviations else 0,
            'avg_frequency_deviation': np.mean(frequency_deviations) if frequency_deviations else 0,
            'frequency_response_adequacy': 'adequate' if max(frequency_deviations) < 0.5 else 'marginal',
            'primary_reserve_requirement': self._calculate_primary_reserve_requirement(max_ramping_rate),
            'secondary_reserve_requirement': self._calculate_secondary_reserve_requirement(max_ramping_rate)
            }

    def _calculate_frequency_deviation(self, ramping_rate: float, inertia_constant: float) -> float:
        """Calculate frequency deviation for a given ramping rate."""
        # Simplified frequency deviation calculation
        # df/dt = -ΔP / (2 * H * f0)
        delta_p = ramping_rate
        h = inertia_constant
        f0 = self.system_parameters['frequency']

        frequency_deviation = abs(delta_p) / (2 * h * f0)
        return frequency_deviation

    def _calculate_primary_reserve_requirement(self, max_ramping_rate: float) -> float:
        """Calculate primary reserve requirement."""
        # Primary reserve should be able to handle largest credible contingency
        return max_ramping_rate * 1.5 # 150% of max ramping rate

    def _calculate_secondary_reserve_requirement(self, max_ramping_rate: float) -> float:
        """Calculate secondary reserve requirement."""
        # Secondary reserve for longer-term frequency control
        return max_ramping_rate * 0.5 # 50% of max ramping rate

    def _calculate_voltage_stability(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate voltage stability margins."""
        # Calculate voltage stability index
        peak_load = load_forecast['consumption'].max()
        avg_load = load_forecast['consumption'].mean()

        # Simulate voltage stability margin
        voltage_stability_margin = self._calculate_voltage_stability_margin(peak_load, system_data)

        # Calculate voltage sensitivity
        voltage_sensitivity = self._calculate_voltage_sensitivity(load_forecast, system_data)

        return {
        'voltage_stability_margin': voltage_stability_margin,
        'voltage_sensitivity': voltage_sensitivity,
        'critical_load_level': peak_load * 1.2, # 120% of peak load
        'voltage_stability_adequacy': 'adequate' if voltage_stability_margin > 0.1 else 'marginal',
        'voltage_violation_risk': 'low' if voltage_stability_margin > 0.2 else 'medium'
        }

    def _calculate_voltage_stability_margin(self, peak_load: float, system_data: Dict[str, Any]) -> float:
        """Calculate voltage stability margin."""
        # Simplified voltage stability margin calculation
        system_capacity = sum(gen['capacity'] for gen in system_data.get('generators', []))
        if system_capacity > 0:
            margin = (system_capacity - peak_load) / system_capacity
            return max(0, margin)
            return 0.1 # Default margin

    def _calculate_voltage_sensitivity(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate voltage sensitivity to load changes."""
        # Calculate voltage sensitivity coefficients
        load_variations = load_forecast['consumption'].pct_change().dropna()

        return {
        'voltage_sensitivity_coefficient': 0.02, # 2% voltage change per 1% load change
        'max_voltage_sensitivity': load_variations.max() * 0.02,
        'avg_voltage_sensitivity': load_variations.mean() * 0.02,
        'voltage_sensitivity_adequacy': 'adequate' if abs(load_variations.max()) < 0.1 else 'marginal'
        }

    def _calculate_transient_stability(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate transient stability margins."""
        # Calculate critical clearing time
        critical_clearing_time = self._calculate_critical_clearing_time(system_data)

        # Calculate transient stability margin
        transient_margin = self._calculate_transient_stability_margin(load_forecast, system_data)

        return {
        'critical_clearing_time': critical_clearing_time,
        'transient_stability_margin': transient_margin,
        'transient_stability_adequacy': 'adequate' if transient_margin > 0.15 else 'marginal',
        'fault_tolerance': 'high' if critical_clearing_time > 0.2 else 'medium'
        }

    def _calculate_critical_clearing_time(self, system_data: Dict[str, Any]) -> float:
        """Calculate critical clearing time for transient stability."""
        # Simplified critical clearing time calculation
        system_inertia = self._calculate_system_inertia(system_data)
        inertia_constant = system_inertia['system_inertia_constant']

        # Critical clearing time is inversely proportional to inertia
        critical_clearing_time = 0.3 / inertia_constant # Simplified formula
        return critical_clearing_time

    def _calculate_transient_stability_margin(self, load_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> float:
        """Calculate transient stability margin."""
        peak_load = load_forecast['consumption'].max()
        system_capacity = sum(gen['capacity'] for gen in system_data.get('generators', []))

        if system_capacity > 0:
            margin = (system_capacity - peak_load) / system_capacity
            return max(0, margin)
            return 0.2 # Default margin

    def _calculate_small_signal_stability(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate small signal stability characteristics."""
        # Calculate damping ratios for different modes
        damping_ratios = {
        'local_mode': 0.15, # Local generator modes
        'inter_area_mode': 0.05, # Inter-area modes
        'torsional_mode': 0.10 # Torsional modes
        }

        # Calculate stability margins
        stability_margins = {
        'local_mode_margin': 0.05 if damping_ratios['local_mode'] > 0.1 else 0.02,
        'inter_area_mode_margin': 0.02 if damping_ratios['inter_area_mode'] > 0.03 else 0.01,
        'torsional_mode_margin': 0.03 if damping_ratios['torsional_mode'] > 0.05 else 0.01
        }

        return {
        'damping_ratios': damping_ratios,
        'stability_margins': stability_margins,
        'small_signal_stability_adequacy': 'adequate' if all(dr > 0.05 for dr in damping_ratios.values()) else 'marginal',
        'oscillation_risk': 'low' if min(damping_ratios.values()) > 0.1 else 'medium'
        }

    def _calculate_overall_stability_margin(self, inertia_analysis: Dict[str, Any],
        frequency_response: Dict[str, Any],
        voltage_stability: Dict[str, Any]) -> float:
        """Calculate overall system stability margin."""
        # Weighted combination of different stability margins
        inertia_weight = 0.3
        frequency_weight = 0.4
        voltage_weight = 0.3

        inertia_margin = 0.1 if inertia_analysis['inertia_adequacy'] == 'adequate' else 0.05
        frequency_margin = 0.1 if frequency_response['frequency_response_adequacy'] == 'adequate' else 0.05
        voltage_margin = voltage_stability['voltage_stability_margin']

        overall_margin = (inertia_weight * inertia_margin +
        frequency_weight * frequency_margin +
        voltage_weight * voltage_margin)

        return overall_margin

    def _generate_stability_recommendations(self, inertia_analysis: Dict[str, Any],
        frequency_response: Dict[str, Any],
        voltage_stability: Dict[str, Any]) -> List[str]:
        """Generate stability recommendations."""
        recommendations = []

        if inertia_analysis['inertia_adequacy'] == 'marginal':
            recommendations.append("Consider adding synchronous condensers or energy storage for inertia support")

            if frequency_response['frequency_response_adequacy'] == 'marginal':
                recommendations.append("Increase primary and secondary reserve capacity")

                if voltage_stability['voltage_stability_adequacy'] == 'marginal':
                    recommendations.append("Consider voltage support devices (SVCs, STATCOMs)")

                    if not recommendations:
                        recommendations.append("System stability is adequate for forecasted load")

                        return recommendations

    def analyze_renewable_integration_impact(self, load_forecast: pd.DataFrame,
        renewable_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze impact of renewable energy integration on system stability.

        Args:
        load_forecast: Forecasted load data
        renewable_forecast: Forecasted renewable generation
        system_data: System configuration

        Returns:
        Renewable integration impact analysis
        """
        try:
            # Calculate net load
            net_load = load_forecast['consumption'] - renewable_forecast['generation']

            # Calculate ramping requirements
            ramping_analysis = self._analyze_renewable_ramping(net_load, renewable_forecast)

            # Calculate inertia impact
            inertia_impact = self._analyze_renewable_inertia_impact(renewable_forecast, system_data)

            # Calculate frequency response impact
            frequency_impact = self._analyze_renewable_frequency_impact(net_load, system_data)

            # Calculate voltage impact
            voltage_impact = self._analyze_renewable_voltage_impact(renewable_forecast, system_data)

            return {
            'net_load_profile': net_load.tolist(),
            'ramping_analysis': ramping_analysis,
            'inertia_impact': inertia_impact,
            'frequency_impact': frequency_impact,
            'voltage_impact': voltage_impact,
            'integration_recommendations': self._generate_renewable_integration_recommendations(
            ramping_analysis, inertia_impact, frequency_impact, voltage_impact
            )
            }

        except Exception as e:
            return {'error': f'Renewable integration analysis failed: {str(e)}'}

    def _analyze_renewable_ramping(self, net_load: pd.Series, renewable_forecast: pd.DataFrame) -> Dict[str, Any]:
        """Analyze ramping requirements with renewable integration."""
        net_load_ramping = net_load.diff().abs()
        renewable_ramping = renewable_forecast['generation'].diff().abs()

        return {
        'max_net_load_ramping': net_load_ramping.max(),
        'avg_net_load_ramping': net_load_ramping.mean(),
        'max_renewable_ramping': renewable_ramping.max(),
        'avg_renewable_ramping': renewable_ramping.mean(),
        'ramping_ratio': renewable_ramping.max() / net_load_ramping.max() if net_load_ramping.max() > 0 else 0,
        'ramping_adequacy': 'adequate' if net_load_ramping.max() < net_load.mean() * 0.1 else 'marginal'
        }

    def _analyze_renewable_inertia_impact(self, renewable_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze impact of renewable generation on system inertia."""
        renewable_penetration = renewable_forecast['generation'].mean() / sum(gen['capacity'] for gen in system_data.get('generators', []))

        # Renewable sources typically have lower inertia
        inertia_reduction = renewable_penetration * 0.5 # 50% inertia reduction per unit renewable

        return {
        'renewable_penetration': renewable_penetration,
        'inertia_reduction': inertia_reduction,
        'inertia_impact': 'significant' if inertia_reduction > 0.2 else 'moderate',
        'inertia_compensation_required': inertia_reduction > 0.15
        }

    def _analyze_renewable_frequency_impact(self, net_load: pd.Series, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze frequency response impact of renewable integration."""
        net_load_ramping = net_load.diff().abs()
        max_ramping = net_load_ramping.max()

        # Increased ramping requirements reduce frequency response capability
        frequency_response_reduction = max_ramping / net_load.mean() * 0.1

        return {
        'frequency_response_reduction': frequency_response_reduction,
        'frequency_impact': 'significant' if frequency_response_reduction > 0.05 else 'moderate',
        'additional_reserves_required': frequency_response_reduction > 0.03
        }

    def _analyze_renewable_voltage_impact(self, renewable_forecast: pd.DataFrame,
        system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze voltage impact of renewable integration."""
        renewable_penetration = renewable_forecast['generation'].mean() / sum(gen['capacity'] for gen in system_data.get('generators', []))

        # Renewable sources can cause voltage fluctuations
        voltage_fluctuation = renewable_penetration * 0.02 # 2% voltage fluctuation per unit renewable

        return {
        'voltage_fluctuation': voltage_fluctuation,
        'voltage_impact': 'significant' if voltage_fluctuation > 0.01 else 'moderate',
        'voltage_support_required': voltage_fluctuation > 0.005
        }

    def _generate_renewable_integration_recommendations(self, ramping_analysis: Dict[str, Any],
        inertia_impact: Dict[str, Any],
        frequency_impact: Dict[str, Any],
        voltage_impact: Dict[str, Any]) -> List[str]:
        """Generate recommendations for renewable integration."""
        recommendations = []

        if ramping_analysis['ramping_adequacy'] == 'marginal':
            recommendations.append("Increase flexible generation capacity for ramping support")

            if inertia_impact['inertia_compensation_required']:
                recommendations.append("Deploy synchronous condensers or grid-forming inverters")

                if frequency_impact['additional_reserves_required']:
                    recommendations.append("Increase primary and secondary reserve capacity")

                    if voltage_impact['voltage_support_required']:
                        recommendations.append("Deploy voltage support devices (SVCs, STATCOMs)")

                        if not recommendations:
                            recommendations.append("Renewable integration is feasible with current system configuration")

                            return recommendations
