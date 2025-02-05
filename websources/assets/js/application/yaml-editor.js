// const BASE_URL = 'http://localhost:5007'; // Flask 后端的地址,改用相对路径
const yamlFileSelect = document.getElementById('yamlFileSelect');
const yamlEditor = document.getElementById('yamlEditor');
const saveButton = document.getElementById('saveYaml');
let yamlData = {};
let currentFile = '';

// Load YAML files from the backend
async function fetchYamlFiles() {
  const response = await fetch(`./api/files`);
  const result = await response.json();
  if (result.files) {
    yamlFileSelect.innerHTML = result.files.map(file =>
      `<option value="${file}" ${file === 'basic_config.yaml' ? 'selected' : ''}>${file}</option>`
    ).join('');
    currentFile = yamlFileSelect.value;
    loadYamlFile(currentFile);
  } else {
    alert('Failed to fetch YAML file list.');
  }
}

async function loadYamlFile(fileName) {
  const response = await fetch(`./api/load/${fileName}`);
  const data = await response.json();
  console.log(data)

  if (data) {
    yamlData = data;
    console.log(yamlData)
    renderYamlEditor(yamlData, yamlEditor);
    yamlEditor.style.display = 'block';
    saveButton.style.display = 'inline-block';
  } else {
    alert('Failed to load YAML file.');
  }
}

// Save YAML file to the backend
async function saveYamlFile() {
  const response = await fetch(`./api/save/${currentFile}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(yamlData),
  });
  const result = await response.json();
  if (result.message) {
    alert('File saved successfully!');
  } else {
    alert('Failed to save YAML file.');
  }
}

// Render YAML editor
function renderYamlEditor(data, container) {
  container.innerHTML = '';
  createEditorElements(data.data || data, data.comments || {}, container); // 处理没有 comments 的情况
}

function createEditorElements(data, comments, parent, path = "") {
  const ul = document.createElement('ul');
  ul.classList.add('list-group');

  for (const [key, value] of Object.entries(data)) {
    const li = document.createElement('li');
    li.classList.add('list-group-item', 'd-flex', 'flex-column', 'align-items-start', 'mb-2','border','rounded-3','me-1');

    // 构建当前键的完整路径，只针对 data
    const currentPath = path ? `${path}.${key}` : key;

    // 添加 key 的显示,并添加注释显示
    const keyContainer = document.createElement('div');
    keyContainer.classList.add('d-flex', 'align-items-center', 'w-100'); // 添加 w-100 使其宽度撑满
    const keyLabel = document.createElement('h5');
    keyLabel.textContent = `${key}:`;
    keyLabel.classList.add('me-2');
    keyContainer.appendChild(keyLabel);

    // 使用 data 的路径查找注释
    const commentKey = currentPath; // 注释的键直接使用当前路径
    const comment = comments ? comments[commentKey] : null;
    if (comment) {
      //检测注释中有没有链接，若有，替换成超链接样式
      var reg = /(http:\/\/|https:\/\/)((\w|=|\?|\.|\/|&|-)+)/g;
      var commentWithLink = comment;
      commentWithLink = commentWithLink.replace(reg, `<a class="ms-2 me-2" href="$1$2" style="text-decoration:underline dotted;" target="_blank"><span>$1$2</span></a>`).replace(/\n/g, "<br />");
      // 添加注释文本
      const commentText = document.createElement('span');
      commentText.classList.add('text-muted', 'ms-2','me-2');
      commentText.style.fontSize = '0.9rem';
      commentText.style.whiteSpace = 'pre-wrap';
      commentText.innerHTML = commentWithLink;



      keyContainer.appendChild(commentText);
    }

    li.appendChild(keyContainer);

    // 创建一个 div 容器来包裹 input
    const inputCommentContainer = document.createElement('div');
    inputCommentContainer.classList.add('d-flex', 'align-items-center', 'flex-grow-1', 'w-100','mt-1','markkk');

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      if (typeof value === 'boolean') {

        //bootstrap样式
        //<input class="form-check-input mt-1 ms-auto" type="checkbox">
        const toggle_container = document.createElement('div');
        toggle_container.classList.add('form-check','form-switch','ps-0','is-filled','ms-1','my-1');
        const toggle = document.createElement('input');
        toggle.classList.add('form-check-input','ms-auto');
        toggle.type="checkbox";
        toggle.checked=value;
        toggle_container.appendChild(toggle);
        inputCommentContainer.appendChild(toggle_container);
        
        // // 创建一个 select 元素
        // const select = document.createElement('select');
        // select.classList.add('form-select', 'form-select-sm');
        // select.style.width = 'auto'; // 设置宽度为自动

        // // 创建 option 元素
        // const optionTrue = document.createElement('option');
        // optionTrue.value = 'true';
        // optionTrue.text = 'true';
        // optionTrue.selected = value === true;

        // const optionFalse = document.createElement('option');
        // optionFalse.value = 'false';
        // optionFalse.text = 'false';
        // optionFalse.selected = value === false;

        // // 将 option 元素添加到 select 元素中
        // select.appendChild(optionTrue);
        // select.appendChild(optionFalse);

        // 添加事件监听器，当值改变时更新数据
        toggle.addEventListener('change', (e) => {
          const value = e.target.checked;
          console.log(data+currentPath+value);
          updateData(yamlData.data, currentPath, value);
        });

        // inputCommentContainer.appendChild(select);
      } else {
        const itemContainer = document.createElement('div');
        itemContainer.classList.add('d-flex', 'align-items-center', 'mt-1','input-group','input-group-outline');
        // 创建一个 input 元素
        const input = document.createElement('input');
        input.type = typeof value === 'number' ? 'number' : 'text';
        input.value = value;
        input.classList.add('form-control', 'form-control-sm');
        itemContainer.appendChild(input);
        inputCommentContainer.appendChild(itemContainer);
        // 添加事件监听器，当值改变时更新数据
        input.addEventListener('input', (e) => {
          updateData(yamlData.data, currentPath, typeof value === 'number' ? parseFloat(e.target.value) : e.target.value);
        });

      }
      li.appendChild(inputCommentContainer);

    } else if (Array.isArray(value)) {
      const listContainer = document.createElement('div');
      listContainer.classList.add('flex-grow-1', 'w-100');
      value.forEach((item, index) => {
        const itemContainer = document.createElement('div');
        itemContainer.classList.add('d-flex', 'align-items-center', 'mt-1','input-group','input-group-outline');

        const itemInput = document.createElement('input');
        itemInput.type = 'text';
        itemInput.value = item;
        itemInput.classList.add('form-control','form-control-sm');
        itemInput.addEventListener('input', (e) => {
          updateData(yamlData.data, `${currentPath}[${index}]`, e.target.value);
        });

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.type="button";
        deleteButton.classList.add('btn', 'btn-danger','btn-sm');
        deleteButton.addEventListener('click', () => {
          value.splice(index, 1);
          renderYamlEditor(yamlData, yamlEditor); // 重新渲染以反映更改
        });

        itemContainer.appendChild(itemInput);
        itemContainer.appendChild(deleteButton);
        listContainer.appendChild(itemContainer);
      });

      const addButton = document.createElement('button');
      addButton.textContent = 'Add Item';
      addButton.classList.add('btn', 'btn-success', 'btn-sm', 'mt-2');
      addButton.addEventListener('click', () => {
        value.push(''); // 添加一个空字符串作为新项
        renderYamlEditor(yamlData, yamlEditor); // 重新渲染以反映更改
      });

      listContainer.appendChild(addButton);
      li.appendChild(listContainer);

    } else if (typeof value === 'object') {
      const nestedContainer = document.createElement('div');
      nestedContainer.classList.add('ms-3', 'mt-2', 'flex-grow-1', 'w-100');
      // 对对象类型递归调用 createEditorElements
      createEditorElements(value, comments, nestedContainer, currentPath);
      li.appendChild(nestedContainer);
    }

    ul.appendChild(li);
  }

  parent.appendChild(ul);
  // 不需要在这里初始化 tooltip，因为注释不再使用 tooltip
}

// 更新数据的辅助函数
function updateData(data, path, newValue) {
  console.log("update");
  const pathParts = path.split('.');
  let current = data;
  for (let i = 0; i < pathParts.length - 1; i++) {
    if (pathParts[i].includes('[')) {
      // 处理数组路径
      const [key, indexStr] = pathParts[i].split('[');
      const index = parseInt(indexStr.replace(']', ''), 10);
      current = current[key][index];
    } else {
      current = current[pathParts[i]];
    }
  }
  const lastPart = pathParts[pathParts.length - 1];
  if (lastPart.includes('[')) {
    // 处理数组路径
    const [key, indexStr] = lastPart.split('[');
    const index = parseInt(indexStr.replace(']', ''), 10);
    current[key][index] = newValue;
  } else {
    current[lastPart] = newValue;
  }
}

yamlFileSelect.addEventListener('change', (e) => {
  currentFile = e.target.value;
  loadYamlFile(currentFile);
});

saveButton.addEventListener('click', saveYamlFile);

fetchYamlFiles();