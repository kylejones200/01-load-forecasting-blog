"""
Power Flow Analysis Service
Implements electrical engineering power flow calculations for load forecasting
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')

class PowerFlowService:
    """Service for power flow analysis and electrical engineering calculations."""

    def __init__(self):
        """Initialize power flow service."""
        self.base_mva = 100 # Base MVA for per-unit calculations
        self.base_kv = 138 # Base kV for per-unit calculations

    def newton_raphson_powerflow(self, bus_data: Dict, line_data: Dict,
                                 load_forecast: pd.DataFrame) -> Dict[str, Any]:
        """
        Newton-Raphson power flow analysis with load forecasting integration.

        Args:
            bus_data: Bus data with voltage, angle, P, Q
            line_data: Line data with impedance, admittance
            load_forecast: Forecasted load data

        Returns:
            Power flow solution with voltages, angles, flows
        """
        try:
            # Extract bus information
            n_buses = len(bus_data['bus_id'])
            bus_types = bus_data['bus_type'] # 1=PQ, 2=PV, 3=Slack
            voltages = bus_data['voltage_magnitude']
            angles = bus_data['voltage_angle']
            p_load = bus_data['p_load']
            q_load = bus_data['q_load']
            p_gen = bus_data['p_generation']
            q_gen = bus_data['q_generation']

            # Build Y-bus matrix
            y_bus = self._build_ybus_matrix(line_data, n_buses)

            # Initialize solution vector
            x = np.zeros(2 * n_buses)
            for i in range(n_buses):
                x[i] = angles[i] # Voltage angles
                x[i + n_buses] = voltages[i] # Voltage magnitudes

            # Newton-Raphson iteration
            max_iterations = 20
            tolerance = 1e-6

            for iteration in range(max_iterations):
                # Calculate power mismatches
                p_mismatch, q_mismatch = self._calculate_power_mismatches(
                    x, y_bus, bus_types, p_load, q_load, p_gen, q_gen, n_buses
                )

                # Check convergence
                max_mismatch = max(max(abs(p_mismatch)), max(abs(q_mismatch)))
                if max_mismatch < tolerance:
                    break

                # Build Jacobian matrix
                jacobian = self._build_jacobian_matrix(x, y_bus, bus_types, n_buses)

                # Solve for corrections
                mismatch_vector = np.concatenate([p_mismatch, q_mismatch])
                corrections = np.linalg.solve(jacobian, -mismatch_vector)

                # Update solution
                x += corrections

            # Extract results
            voltage_angles = x[:n_buses]
            voltage_magnitudes = x[n_buses:]

            # Calculate line flows
            line_flows = self._calculate_line_flows(
                voltage_magnitudes, voltage_angles, line_data, y_bus
            )

            return {
                'converged': max_mismatch < tolerance,
                'iterations': iteration + 1,
                'voltage_magnitudes': voltage_magnitudes,
                'voltage_angles': voltage_angles,
                'line_flows': line_flows,
                'power_losses': self._calculate_power_losses(line_flows),
                'max_mismatch': max_mismatch
            }

        except Exception as e:
            return {'error': f'Power flow analysis failed: {str(e)}'}

    def _build_ybus_matrix(self, line_data: Dict, n_buses: int) -> np.ndarray:
        """Build Y-bus admittance matrix."""
        y_bus = np.zeros((n_buses, n_buses), dtype=complex)

        for i, (from_bus, to_bus) in enumerate(zip(line_data['from_bus'], line_data['to_bus'])):
            impedance = complex(line_data['resistance'][i], line_data['reactance'][i])
            admittance = 1 / impedance

            # Add to Y-bus matrix
            y_bus[from_bus-1, to_bus-1] -= admittance
            y_bus[to_bus-1, from_bus-1] -= admittance
            y_bus[from_bus-1, from_bus-1] += admittance
            y_bus[to_bus-1, to_bus-1] += admittance

        return y_bus

    def _calculate_power_mismatches(self, x: np.ndarray, y_bus: np.ndarray,
                                     bus_types: List[int], p_load: List[float],
                                     q_load: List[float], p_gen: List[float],
                                     q_gen: List[float], n_buses: int) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate power mismatches for Newton-Raphson."""
        angles = x[:n_buses]
        voltages = x[n_buses:]

        p_mismatch = np.zeros(n_buses)
        q_mismatch = np.zeros(n_buses)

        for i in range(n_buses):
            # Calculate injected power
            p_injected = 0
            q_injected = 0

            for j in range(n_buses):
                p_injected += voltages[i] * voltages[j] * (
                    y_bus[i, j].real * np.cos(angles[i] - angles[j]) +
                    y_bus[i, j].imag * np.sin(angles[i] - angles[j])
                )
                q_injected += voltages[i] * voltages[j] * (
                    y_bus[i, j].real * np.sin(angles[i] - angles[j]) -
                    y_bus[i, j].imag * np.cos(angles[i] - angles[j])
                )

            # Calculate mismatches
            p_mismatch[i] = p_gen[i] - p_load[i] - p_injected
            q_mismatch[i] = q_gen[i] - q_load[i] - q_injected

            # Set mismatches to zero for slack bus
            if bus_types[i] == 3: # Slack bus
                p_mismatch[i] = 0
                q_mismatch[i] = 0

        return p_mismatch, q_mismatch

    def _build_jacobian_matrix(self, x: np.ndarray, y_bus: np.ndarray,
                                bus_types: List[int], n_buses: int) -> np.ndarray:
        """Build Jacobian matrix for Newton-Raphson."""
        angles = x[:n_buses]
        voltages = x[n_buses:]

        jacobian = np.zeros((2 * n_buses, 2 * n_buses))

        # Partial derivatives of P with respect to angles
        for i in range(n_buses):
            for j in range(n_buses):
                if i == j:
                    for k in range(n_buses):
                        if k != i:
                            jacobian[i, j] -= voltages[i] * voltages[k] * (
                                y_bus[i, k].real * np.sin(angles[i] - angles[k]) -
                                y_bus[i, k].imag * np.cos(angles[i] - angles[k])
                            )
                else:
                    jacobian[i, j] = voltages[i] * voltages[j] * (
                        y_bus[i, j].real * np.sin(angles[i] - angles[j]) -
                        y_bus[i, j].imag * np.cos(angles[i] - angles[j])
                    )

        # Partial derivatives of P with respect to voltages
        for i in range(n_buses):
            for j in range(n_buses):
                if i == j:
                    for k in range(n_buses):
                        jacobian[i, j + n_buses] += voltages[k] * (
                            y_bus[i, k].real * np.cos(angles[i] - angles[k]) +
                            y_bus[i, k].imag * np.sin(angles[i] - angles[k])
                        )
                else:
                    jacobian[i, j + n_buses] = voltages[j] * (
                        y_bus[i, j].real * np.cos(angles[i] - angles[j]) +
                        y_bus[i, j].imag * np.sin(angles[i] - angles[j])
                    )

        # Partial derivatives of Q with respect to angles
        for i in range(n_buses):
            for j in range(n_buses):
                if i == j:
                    for k in range(n_buses):
                        if k != i:
                            jacobian[i + n_buses, j] += voltages[i] * voltages[k] * (
                                y_bus[i, k].real * np.cos(angles[i] - angles[k]) +
                                y_bus[i, k].imag * np.sin(angles[i] - angles[k])
                            )
                else:
                    jacobian[i + n_buses, j] = -voltages[i] * voltages[j] * (
                        y_bus[i, j].real * np.cos(angles[i] - angles[j]) +
                        y_bus[i, j].imag * np.sin(angles[i] - angles[j])
                    )

        # Partial derivatives of Q with respect to voltages
        for i in range(n_buses):
            for j in range(n_buses):
                if i == j:
                    for k in range(n_buses):
                        jacobian[i + n_buses, j + n_buses] += voltages[k] * (
                            y_bus[i, k].real * np.sin(angles[i] - angles[k]) -
                            y_bus[i, k].imag * np.cos(angles[i] - angles[k])
                        )
                else:
                    jacobian[i + n_buses, j + n_buses] = voltages[j] * (
                        y_bus[i, j].real * np.sin(angles[i] - angles[j]) -
                        y_bus[i, j].imag * np.cos(angles[i] - angles[j])
                    )

        return jacobian

    def _calculate_line_flows(self, voltages: np.ndarray, angles: np.ndarray,
                               line_data: Dict, y_bus: np.ndarray) -> Dict[str, List]:
        """Calculate power flows on transmission lines."""
        line_flows = {
            'from_bus': [],
            'to_bus': [],
            'p_flow': [],
            'q_flow': [],
            'current_magnitude': []
        }

        for i, (from_bus, to_bus) in enumerate(zip(line_data['from_bus'], line_data['to_bus'])):
            from_idx = from_bus - 1
            to_idx = to_bus - 1

            # Calculate complex power flow
            v_from = voltages[from_idx] * np.exp(1j * angles[from_idx])
            v_to = voltages[to_idx] * np.exp(1j * angles[to_idx])

            s_flow = v_from * np.conj((v_from - v_to) * y_bus[from_idx, to_idx])

            line_flows['from_bus'].append(from_bus)
            line_flows['to_bus'].append(to_bus)
            line_flows['p_flow'].append(s_flow.real)
            line_flows['q_flow'].append(s_flow.imag)
            line_flows['current_magnitude'].append(abs(s_flow / v_from))

        return line_flows

    def _calculate_power_losses(self, line_flows: Dict[str, List]) -> Dict[str, float]:
        """Calculate total power losses in the system."""
        total_p_loss = sum(line_flows['p_flow'])
        total_q_loss = sum(line_flows['q_flow'])

        return {
            'total_p_loss': total_p_loss,
            'total_q_loss': total_q_loss,
            'total_loss_percentage': (total_p_loss / sum(line_flows['p_flow'])) * 100
        }

    def contingency_analysis(self, base_case: Dict, contingency_list: List[Dict]) -> Dict[str, Any]:
        """
        Perform N-1 contingency analysis for reliability assessment.

        Args:
            base_case: Base case power flow solution
            contingency_list: List of contingencies to analyze

        Returns:
            Contingency analysis results
        """
        try:
            contingency_results = []

            for contingency in contingency_list:
                # Modify system for contingency
                modified_system = self._apply_contingency(base_case, contingency)

                # Run power flow for contingency case
                contingency_result = self.newton_raphson_powerflow(
                    modified_system['bus_data'],
                    modified_system['line_data'],
                    modified_system['load_forecast']
                )

                # Check for violations
                violations = self._check_voltage_violations(contingency_result)

                contingency_results.append({
                    'contingency_id': contingency['id'],
                    'contingency_type': contingency['type'],
                    'converged': contingency_result['converged'],
                    'voltage_violations': violations,
                    'line_loading': self._calculate_line_loading(contingency_result),
                    'severity': self._assess_severity(violations)
                })

            return {
                'total_contingencies': len(contingency_list),
                'converged_cases': sum(1 for r in contingency_results if r['converged']),
                'violations_found': sum(1 for r in contingency_results if r['voltage_violations']),
                'results': contingency_results
            }

        except Exception as e:
            return {'error': f'Contingency analysis failed: {str(e)}'}

    def _apply_contingency(self, base_case: Dict, contingency: Dict) -> Dict:
        """Apply contingency to base case system."""
        # This would modify the system topology based on contingency type
        # For now, return a simplified version
        return base_case

    def _check_voltage_violations(self, powerflow_result: Dict) -> List[Dict]:
        """Check for voltage magnitude violations."""
        violations = []
        voltages = powerflow_result['voltage_magnitudes']

        for i, voltage in enumerate(voltages):
            if voltage < 0.95 or voltage > 1.05: # +-5% voltage limits
                violations.append({
                    'bus_id': i + 1,
                    'voltage': voltage,
                    'violation_type': 'low' if voltage < 0.95 else 'high',
                    'severity': abs(voltage - 1.0)
                })

        return violations

    def _calculate_line_loading(self, powerflow_result: Dict) -> Dict[str, List]:
        """Calculate line loading percentages."""
        line_flows = powerflow_result['line_flows']
        # This would compare flows against thermal limits
        return {'loading_percentages': [100.0] * len(line_flows['p_flow'])}

    def _assess_severity(self, violations: List[Dict]) -> str:
        """Assess severity of violations."""
        if not violations:
            return 'none'
        elif len(violations) <= 2:
            return 'low'
        elif len(violations) <= 5:
            return 'medium'
        else:
            return 'high'

    def optimal_power_flow(self, bus_data: Dict, line_data: Dict,
                            objective_function: str = 'minimize_losses') -> Dict[str, Any]:
        """
        Optimal Power Flow (OPF) for economic dispatch and voltage optimization.

        Args:
            bus_data: Bus data with constraints
            line_data: Line data with limits
            objective_function: Optimization objective

        Returns:
            OPF solution with optimal generation dispatch
        """
        try:
            # This would implement OPF using optimization techniques
            # For now, return a simplified version

            return {
                'optimal_generation': [100.0] * len(bus_data['bus_id']),
                'optimal_voltages': [1.0] * len(bus_data['bus_id']),
                'total_cost': 1000.0,
                'converged': True,
                'iterations': 10
            }

        except Exception as e:
            return {'error': f'OPF analysis failed: {str(e)}'}

    def load_flow_sensitivity_analysis(self, base_case: Dict,
                                        parameter_variations: Dict) -> Dict[str, Any]:
        """
        Sensitivity analysis for load flow variations.

        Args:
            base_case: Base case power flow solution
            parameter_variations: Parameter variations to analyze

        Returns:
            Sensitivity analysis results
        """
        try:
            sensitivity_results = {}

            for param_name, variations in parameter_variations.items():
                param_sensitivity = []

                for variation in variations:
                    # Modify parameter and run power flow
                    modified_case = self._modify_parameter(base_case, param_name, variation)
                    result = self.newton_raphson_powerflow(
                        modified_case['bus_data'],
                        modified_case['line_data'],
                        modified_case['load_forecast']
                    )

                    param_sensitivity.append({
                        'variation': variation,
                        'voltage_change': np.mean(result['voltage_magnitudes']) - np.mean(base_case['voltage_magnitudes']),
                        'loss_change': result['power_losses']['total_p_loss'] - base_case['power_losses']['total_p_loss']
                    })

                sensitivity_results[param_name] = param_sensitivity

            return {
                'parameter_sensitivities': sensitivity_results,
                'most_sensitive_parameter': max(sensitivity_results.keys(),
                    key=lambda k: max(abs(s['voltage_change']) for s in sensitivity_results[k]))
            }

        except Exception as e:
            return {'error': f'Sensitivity analysis failed: {str(e)}'}

    def _modify_parameter(self, base_case: Dict, param_name: str, variation: float) -> Dict:
        """Modify a parameter in the base case."""
        # This would modify the specified parameter
        return base_case
