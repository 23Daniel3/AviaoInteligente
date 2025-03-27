package aviao.util;

import org.apache.commons.math3.analysis.polynomials.PolynomialFunction;
import org.apache.commons.math3.analysis.polynomials.PolynomialSplineFunction;

import java.util.function.Supplier;

public class ThrottleMap {

    private final double[] xValuesSupplier;
    private final double[] yValuesSupplier;
    private PolynomialSplineFunction throttleCurve;

    public ThrottleMap(double[] xValues, double[] yValues) {
        this.xValuesSupplier = xValues;
        this.yValuesSupplier = yValues;
        updateThrottleCurve();
    }

    private void updateThrottleCurve() {
        double[] xValues = xValuesSupplier;
        double[] yValues = yValuesSupplier;
        PolynomialFunction[] polynomials = new PolynomialFunction[xValues.length - 1];

        for (int i = 0; i < polynomials.length; i++) {
            double a = yValues[i];
            double b = (yValues[i + 1] - yValues[i]) / (xValues[i + 1] - xValues[i]);
            polynomials[i] = new PolynomialFunction(new double[]{a, b});
        }
        throttleCurve = new PolynomialSplineFunction(xValues, polynomials);
    }

    public double applyThrottle(Supplier<Double> input) {
        return throttleCurve.value(Math.min(1.0, Math.max(0.0, input.get())));
    }

    public double applyThrottleAbs(Supplier<Double> input) {
        double magnitude = Math.min(1.0, Math.max(0.0, Math.abs(input.get())));
        return Math.copySign(throttleCurve.value(magnitude), input.get());
    }
}
