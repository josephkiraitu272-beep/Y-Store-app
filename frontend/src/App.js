import React, { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { Toaster } from "sonner";
import { HelmetProvider } from "react-helmet-async";
import { LanguageProvider } from "./contexts/LanguageContext";
import { AuthProvider } from "./contexts/AuthContext";
import { CartProvider } from "./contexts/CartContext";
import { FavoritesProvider } from "./contexts/FavoritesContext";
import { ComparisonProvider } from "./contexts/ComparisonContext";
import { NotificationsProvider } from "./contexts/NotificationsContext";
import { CatalogProvider } from "./contexts/CatalogContext";
// RETAIL LAYOUT CORE v3: Header + MegaMenu + Mobile
import HeaderCore from "./components/layout/HeaderCore";
import Footer from "./components/Footer";
import WelcomeModal from "./components/WelcomeModal";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import ProductPageV3 from "./pages/ProductPageV3";
import Favorites from "./pages/Favorites";
import Comparison from "./pages/Comparison";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import CheckoutV2 from "./pages/CheckoutV2";
import CheckoutV3 from "./pages/CheckoutV3";
import CheckoutSuccess from "./pages/CheckoutSuccess";
import AuthCallback from "./pages/AuthCallback";
import AdminPanel from "./pages/AdminPanelRefactored";
import UserProfile from "./pages/UserProfile";
import ContactInfo from "./pages/ContactInfo";
import DeliveryPayment from "./pages/DeliveryPayment";
import ExchangeReturn from "./pages/ExchangeReturn";
import AboutUs from "./pages/AboutUs";
import Terms from "./pages/Terms";
import Promotions from "./pages/Promotions";
import PromotionDetail from "./pages/PromotionDetail";
import OfferDetail from "./pages/OfferDetail";
import SectionDetail from "./pages/SectionDetail";
import NotFound from "./pages/NotFound";
import PickupControlPage from "./pages/PickupControlPage";
import PaymentResume from "./pages/PaymentResume";
import ScrollToTop from "./components/ScrollToTop";
import FloatingActionButton from "./components/FloatingActionButton";
import analyticsTracker from "./services/analyticsTracker";
// V2 Pages
import Account from "./pages/Account";
import AccountOrders from "./pages/AccountOrders";
import OrderDetails from "./pages/OrderDetails";
import CatalogV3 from "./pages/CatalogV3";
// Orders Page for customers
import OrdersPage from "./pages/OrdersPage";
// V2-19: Compare Bar
import CompareBar from "./components/compare/CompareBar";
// V2-19: Search Results
import SearchResults from "./pages/SearchResults";
// B12: Product Page V4
import ProductPageV4 from "./pages/ProductPageV4";
// B16: Mobile components
import { BottomNav, MobileSearchOverlay } from "./components/mobile";
import useIsMobile from "./hooks/useIsMobile";
// Telegram Mini App (NEW mobile-first)
import TMAApp from "./tma-mobile/App";
import "./App.css";

// Analytics Wrapper Component
function AnalyticsWrapper({ children }) {
  const location = useLocation();

  useEffect(() => {
    const pageTitle = document.title;
    analyticsTracker.trackPageView(location.pathname, pageTitle, {
      search: location.search,
      hash: location.hash,
    });
  }, [location]);

  return children;
}

// Main App Content with mobile features
function AppContent() {
  const isMobile = useIsMobile();
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const location = useLocation();

  // Hide bottom nav on checkout
  const hideBottomNav = location.pathname.startsWith("/checkout");

  // Hide header/footer on admin pages
  const isAdminPage = location.pathname.startsWith("/admin");

  // Hide everything for Telegram Mini App — it has its own shell
  const isTMA = location.pathname.startsWith("/tma");

  // Add mobile class to body for bottom nav padding
  useEffect(() => {
    if (isMobile && !hideBottomNav && !isAdminPage && !isTMA) {
      document.body.classList.add("has-bottom-nav");
    } else {
      document.body.classList.remove("has-bottom-nav");
    }

    return () => {
      document.body.classList.remove("has-bottom-nav");
    };
  }, [isMobile, hideBottomNav, isAdminPage, isTMA]);

  // Render standalone TMA shell
  return (
    <Routes>
      <Route path="/tma/*" element={<TMAApp />} />
      <Route path="/*" element={<Navigate to="/tma" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <HelmetProvider>
      <BrowserRouter>
        <LanguageProvider>
          <AuthProvider>
            <NotificationsProvider>
              <ComparisonProvider>
                <FavoritesProvider>
                  <CatalogProvider>
                    <CartProvider>
                      <AnalyticsWrapper>
                        <AppContent />
                      </AnalyticsWrapper>
                    </CartProvider>
                  </CatalogProvider>
                </FavoritesProvider>
              </ComparisonProvider>
            </NotificationsProvider>
          </AuthProvider>
        </LanguageProvider>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
