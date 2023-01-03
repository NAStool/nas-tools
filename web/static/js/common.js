
/**
 * selectgroup全选按钮绑定
 * @param: btnobj 按钮对象
 * @param: id  selectgroup元素id
 **/
function selectgroup_selectALL(btnobj, id) {
  const selobj = $("#" + id);
  if ($(btnobj).text() === "全选") {
    selobj.find("input[type=checkbox]").each(function () {
      $(this).prop("checked", true);
    });
    $(btnobj).text("全不选");
  } else {
    selobj.find("input[type=checkbox]").each(function () {
      $(this).prop("checked", false);
    });
    $(btnobj).text("全选");
  }
}

/**
 * 对象数组排序，针对纯英文、数字或纯中文的排序
 * @param: objArr 需要排序的对象数组
 * @param: sortKey  需要进行排序的键
 * @param: sortType asc升序(默认)  desc 降序
 **/
function dictArraySorting(objArr,sortKey,sortType="asc") {
  return objArr.sort(function (obj1, obj2) {
    let val1 = obj1[sortKey];
    let val2 = obj2[sortKey];
    if (!isNaN(Number(val1)) && !isNaN(Number(val2))) {
        val1 = Number(val1);
        val2 = Number(val2);
    }
    if (sortType === "asc") {
      return val1 - val2;
    } else if (sortType === "desc") {
      return val2 - val1;
    }
  })
}

/**
 * bytes转换为size
 * @param: bytes 字节数
 **/
function bytesToSize(bytes) {
    let size = ''
    if (bytes < 0.1 * 1024) { // 小于0.1KB 则转化成B
      size = bytes + ' B'
    }
    else if (bytes < 0.1 * 1024 * 1024) { // 小于0.1MB 则转换成KB
      size = (bytes / 1024).toFixed(2) + ' KB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024) { // 小于0.1GB 则转换成MB
      size = (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024) { // 小于0.1TB 则转换成GB
      size = (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1PB 则转换成TB
      size = (bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2) + ' TB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1EB 则转换成PB
      size = (bytes / (1024 * 1024 * 1024 * 1024 * 1024)).toFixed(2) + ' PB'
    }
    return size
  }

