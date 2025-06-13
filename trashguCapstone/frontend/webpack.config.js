// File: frontend/webpack.config.js
const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
  entry: "./src/js/index.js",
  output: {
    path: path.resolve(__dirname, "dist"),
    filename: "bundle.js",
    clean: true,
    assetModuleFilename: "assets/images/[hash][ext][query]",
  },
  devServer: {
    static: {
      directory: path.join(__dirname, "dist"),
    },
    port: 3000,
    open: true,
    historyApiFallback: true,
  },
  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader", "postcss-loader"],
      },
      {
        test: /\.(png|svg|jpg|jpeg|gif)$/i,
        type: "asset/resource",
      },
      {
        test: /\.html$/i,
        loader: "html-loader",
      },
    ],
  },
  plugins: [
    // === PERBAIKAN: Path template diubah, tidak lagi menggunakan './src/' ===
    new HtmlWebpackPlugin({
      template: "./src/index.html", // Path relatif dari root frontend
      filename: "index.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/tim-teknologi.html",
      filename: "tim-teknologi.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/klasifikasi.html",
      filename: "klasifikasi.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/hasil-klasifikasi.html",
      filename: "hasil-klasifikasi.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/login.html",
      filename: "login.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/registrasi.html",
      filename: "registrasi.html",
      chunks: ["main"],
    }),
    new HtmlWebpackPlugin({
      template: "./src/dashboard.html",
      filename: "dashboard.html",
      chunks: ["main"],
    }),
    // ======================================================================
  ],
  mode: "development",
};
