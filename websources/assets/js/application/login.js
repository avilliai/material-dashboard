document.addEventListener('DOMContentLoaded', function () {

  const loginButton = document.getElementById('login');


  loginButton.addEventListener('click', async () => {

    const accountInput = document.getElementById('account');
    const passwordInput = document.getElementById('password');

    const account = accountInput.value;
    const password = passwordInput.value;
    const encryptedPassword = sha3_256(password);

    try {

      const response = await fetch('./api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          account: account,
          password: encryptedPassword
        })
      });

      // 解析响应数据
      const data = await response.json();

      // 检查服务端响应
      if (data.message === 'Success') {
        localStorage.setItem('auth_token', getCookie('auth_token'));
        // 登录成功，跳转到主页
        showAlert('alert-success','登录成功')
        window.location.href = './';
      } else {
        showAlert('alert-danger','账户名或密码错误')
      }
    } catch (error) {
      showAlert('alert-danger','网络连接出错')
    }
  });
})
