import { Link } from "react-router-dom"
import ThemeToggle from './ThemeToggle';

function Navbar({ theme = 'light' }){
    const isAuthenticated = localStorage.getItem('token')
    const name = localStorage.getItem('name')
    const userRole = localStorage.getItem('role')

    const logout = () =>{
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('name')
      localStorage.removeItem('role')
      window.location.href = '/'
    }

    const getDashboardLink = () => {
      switch(userRole) {
        case 'PATIENT':
          return '/patient-dashboard';
        case 'DOCTOR':
          return '/doctor-dashboard';
        case 'HOSPITAL_ADMIN':
          return '/admin-dashboard';
        default:
          return '/patient-profile';
      }
    }

    const getDashboardText = () => {
      return 'Dashboard';
    }

    return (
  <div className={`navigation bg-[#EFF6FF] dark:bg-gray-900 dark:text-white ${theme === 'dark' ? 'dark' : ''}`}>
          <div className="header flex justify-between px-[100px] py-[30px] items-center">
          <div className="header-item flex items-center gap-3">

            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
             <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
             </svg>
            </div>

            <h4 className="font-bold">
              <Link to="/" className="nav-link">
                CureShieldSynapse
              </Link>
            </h4>
          </div>
          <div className="header-item flex gap-10">
            <Link
              to="/"
              className="nav-link hover:text-[#1E40AF] transition-all-duration-300"
            >
              Home
            </Link>
            {isAuthenticated && (
              <>
                <Link
                  to={getDashboardLink()}
                  className="nav-link hover:text-[#1E40AF] transition-all-duration-300"
                >
                  {getDashboardText()}
                </Link>
                <Link
                  to="/prediction"
                  className="nav-link hover:text-[#1E40AF] transition-all-duration-300"
                >
                  Symptom Checker
                </Link>
              </>
            )}
            <Link
              to="/doctors"
              className="nav-link hover:text-[#1E40AF] transition-all-duration-300"
            >
              Doctors
            </Link>
          </div>

          <div className="flex items-center gap-8">
            <ThemeToggle theme={theme} />
            {!isAuthenticated ? (
              <div className="header-item flex gap-10">
                <Link
                  to="/signup"
                  className="hover:text-[#1E40AF] transition-all-duration-300"
                >
                  Signup
                </Link>
                <Link
                  to="/login"
                  className="hover:text-[#1E40AF] transition-all-duration-300"
                >
                  Login
                </Link>
              </div>
            ) : (
              <div className="header-item flex gap-8 items-center">
                <div className="user">
                  <Link to={getDashboardLink()}>
                    <div className="account flex gap-3 items-center">
                      <img src="/images/user.png" alt="" className="w-6 h-6" />
                      <p className="text-black">
                        {userRole === 'DOCTOR' ? `Dr. ${name}` : name}
                      </p>
                    </div>
                  </Link>
                </div>
                <button onClick={logout}>Logout</button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
}

export default Navbar