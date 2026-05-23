//! PyO3 bindings for SAIDI/SAIFI kernels.

use load_forecasting_blog_core::{saidi_saifi_by_key, SaidiSaifiResult};
use numpy::{PyArray1, PyReadonlyArray1, IntoPyArray};
use pyo3::prelude::*;

#[pyfunction]
fn saidi_saifi_by_key_py<'py>(
    py: Python<'py>,
    group_key: PyReadonlyArray1<i64>,
    customers_out: PyReadonlyArray1<f64>,
    slot_minutes: PyReadonlyArray1<f64>,
    customers_served: PyReadonlyArray1<f64>,
) -> PyResult<(
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
)> {
    let r: SaidiSaifiResult = saidi_saifi_by_key(
        group_key.as_slice()?,
        customers_out.as_slice()?,
        slot_minutes.as_slice()?,
        customers_served.as_slice()?,
    );
    Ok((
        r.keys.into_pyarray(py),
        r.saidi_min.into_pyarray(py),
        r.saifi_events_per_cust.into_pyarray(py),
    ))
}

#[pyfunction]
#[pyo3(signature = (group_key, customers_out, slot_minutes, customers_served, iterations=10_000))]
fn bench_kernel_py(
    group_key: PyReadonlyArray1<i64>,
    customers_out: PyReadonlyArray1<f64>,
    slot_minutes: PyReadonlyArray1<f64>,
    customers_served: PyReadonlyArray1<f64>,
    iterations: usize,
) -> PyResult<f64> {
    let g = group_key.as_slice()?.to_vec();
    let co = customers_out.as_slice()?.to_vec();
    let sm = slot_minutes.as_slice()?.to_vec();
    let cs = customers_served.as_slice()?.to_vec();
    let start = std::time::Instant::now();
    for _ in 0..iterations {
        let _ = saidi_saifi_by_key(&g, &co, &sm, &cs);
    }
    Ok(start.elapsed().as_secs_f64())
}

#[pymodule]
fn load_forecasting_blog_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(saidi_saifi_by_key_py, m)?)?;
    m.add_function(wrap_pyfunction!(bench_kernel_py, m)?)?;
    Ok(())
}
