"""
予測モデルモジュール
ローリングウィンドウで学習し、翌日の日本ETFリターンを予測する。

実装モデル:
  - SimpleLinearPredictor: 各日本ETFに対して米国ETFリターンで線形回帰
  - PCAPredictor: 主成分分析で特徴量を圧縮してから線形回帰（論文の拡張版への足がかり）

将来拡張:
  - SubspacePCAPredictor: 部分空間正則化付きPCA（論文手法）を追加可能
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


class RollingPredictor:
    """
    ローリングウィンドウ予測の基底クラス。
    サブクラスで _fit_predict_single を実装すること。
    """

    def __init__(self, window: int = 252):
        """
        Parameters
        ----------
        window : int
            学習に使う過去の営業日数（デフォルト252日 = 約1年）
        """
        self.window = window

    def predict_all(
        self,
        X: pd.DataFrame,
        Y: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        ローリングウィンドウで全期間の予測スコアを生成する。

        Parameters
        ----------
        X : pd.DataFrame
            特徴量（米国ETFのラグリターン）
        Y : pd.DataFrame
            ターゲット（日本ETFの日中リターン）

        Returns
        -------
        pd.DataFrame
            予測スコア。インデックスはYと同じ日付。
        """
        n = len(X)
        pred_list = []

        for i in range(self.window, n):
            X_train = X.iloc[i - self.window : i].values
            Y_train = Y.iloc[i - self.window : i].values
            X_test = X.iloc[i : i + 1].values

            # 未来データリーク防止: テストは常にi日目のみ
            pred_row = self._fit_predict_single(X_train, Y_train, X_test)
            pred_list.append(pred_row)

        preds = np.vstack(pred_list)
        pred_df = pd.DataFrame(
            preds,
            index=Y.index[self.window :],
            columns=Y.columns,
        )
        return pred_df

    def _fit_predict_single(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        X_test: np.ndarray,
    ) -> np.ndarray:
        raise NotImplementedError


class SimpleLinearPredictor(RollingPredictor):
    """
    各日本ETFに対して独立に線形回帰（Ridge）を行うシンプルな予測モデル。
    """

    def __init__(self, window: int = 252, alpha: float = 1.0):
        super().__init__(window)
        self.alpha = alpha

    def _fit_predict_single(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        X_test: np.ndarray,
    ) -> np.ndarray:
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        preds = []
        for j in range(Y_train.shape[1]):
            model = Ridge(alpha=self.alpha)
            model.fit(X_train_s, Y_train[:, j])
            preds.append(model.predict(X_test_s)[0])

        return np.array(preds)


class PCAPredictor(RollingPredictor):
    """
    PCAで特徴量を圧縮してからRidge回帰を行うモデル。
    論文の「部分空間正則化付きPCA」への拡張基盤となる実装。

    論文の手法との対応:
      - PCAによる次元圧縮 → 部分空間への射影（論文の核心）
      - Ridge正則化 → 部分空間正則化の簡易版
      将来的に SubspacePCAPredictor クラスを追加することで論文完全再現が可能。
    """

    def __init__(self, window: int = 252, n_components: int = 5, alpha: float = 1.0):
        super().__init__(window)
        self.n_components = n_components
        self.alpha = alpha

    def _fit_predict_single(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        X_test: np.ndarray,
    ) -> np.ndarray:
        n_comp = min(self.n_components, X_train.shape[1], X_train.shape[0] - 1)

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("pca", PCA(n_components=n_comp)),
            ("ridge", Ridge(alpha=self.alpha)),
        ])

        preds = []
        for j in range(Y_train.shape[1]):
            pipeline.fit(X_train, Y_train[:, j])
            preds.append(pipeline.predict(X_test)[0])

        return np.array(preds)


def run_prediction(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_cols: list[str],
    model_name: str = "pca",
    window: int = 252,
    n_components: int = 5,
    alpha: float = 1.0,
) -> pd.DataFrame:
    """
    指定モデルでローリング予測を実行し、予測スコアのDataFrameを返す。

    Parameters
    ----------
    model_name : str
        "linear" または "pca"
    """
    X = df[feature_cols].copy()
    Y = df[target_cols].copy()

    if model_name == "linear":
        predictor = SimpleLinearPredictor(window=window, alpha=alpha)
    elif model_name == "pca":
        predictor = PCAPredictor(window=window, n_components=n_components, alpha=alpha)
    else:
        raise ValueError(f"未知のモデル名: {model_name}")

    print(f"ローリング予測実行中（モデル: {model_name}, ウィンドウ: {window}日）...")
    predictions = predictor.predict_all(X, Y)
    print(f"予測完了: {len(predictions)} 日分")

    return predictions
