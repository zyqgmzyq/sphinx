# 注解(Annotation)

Java注解（Annotation）又称Java标注，是JDK1.5引入的一种注释机制

Java语言的类、方法、变量、参数和包等都可以被标注，和JavaDoc不同，Java标注可以通过反射获取标注内容，在编译器生成类文件时，标注可以被嵌入到字节码中。Java虚拟机可以保留标注内容，当然它也支持自定义Java标注

## 1 内置的注解

Java定义了一套注解，共有7个，3个在java.lang中，剩下4个在java.lang.annotation中

### 1.1 作用在代码的注解是

```
@Override
检查该方法是否是重写方法，如果发现其父类，或者是引用的接口中并没有该方法，会编译报错
@Deprecated
标记过时方法，如果使用该方法，会报编译警告
@SuppressWarnings
指示编译器去忽略注解中声明的警告
```

### 1.2 作用在其他注解的注解（或者说是元注解）

```
@Retention
@Retention(RetentionPolicy.RUNTIME) 运行时通过反射访问
@Retention(RetentionPolicy.SOURCE) 
@Retention(RetentionPolicy.CLASS) 
标记这个注解怎么保存，是只在代码中，还是编入class文件中，或者是在运行时可以通过反射访问
@Documented
标记这些注解是否包含在用户文档中
@Target
标记这个注解应该是哪种Java成员
@Inherited
标记这个注解是继承于哪个注解类（默认 注解没有继承于任何子类）
```

### 1.3 从Java 7开始，额外添加了3个注解

```
@SafeVarargs
Java7开始支持，忽略任何使用参数为泛型变量的方法或构造函数调用的警告
@FuncationalInterface
Java8开始支持，标识一个匿名函数或函数式接口
@Repeatable
Java8开始支持，标识某注解可以在同一个声明上使用多次
```

## 2 自定义注解

### 2.1 示例

```java
@Documented
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
public @interface MyAnnotation1 {
}
```

上面的作用是定义一个Annotation，它的名字是MyAnnotation1，定义了MyAnnotation1之后，我们可以在代码中通过`@MyAnnotation1`来使用它，其他的，`@Documented`,`@Traget`,`@Retention`,`@interface`都是来修饰MyAnnotation1的，下面说说它们的含义：

#### 2.1.1 @interface

```
使用 @interface 定义注解时，意味着它实现了 java.lang.annotation.Annotation 接口，即该注解就是一个Annotation。
定义 Annotation 时，@interface 是必须的。
注意：它和我们通常的 implemented 实现接口的方法不同。Annotation 接口的实现细节都由编译器完成。通过 @interface 定义注解后，该注解不能继承其他的注解或接口。
```

#### 2.1.2 @Documented

```
类和方法的 Annotation 在缺省情况下是不出现在 javadoc 中的。如果使用 @Documented 修饰该 Annotation，则表示它可以出现在 javadoc 中。

定义 Annotation 时，@Documented 可有可无；若没有定义，则 Annotation 不会出现在 javadoc 中。
```

#### 2.1.3 @Target(ElementType.TYPE)

```
前面我们说过，ElementType 是 Annotation 的类型属性。而 @Target 的作用，就是来指定 Annotation 的类型属性。

@Target(ElementType.TYPE) 的意思就是指定该 Annotation 的类型是 ElementType.TYPE。这就意味着，MyAnnotation1 是来修饰"类、接口（包括注释类型）或枚举声明"的注解。

定义 Annotation 时，@Target 可有可无。若有 @Target，则该 Annotation 只能用于它所指定的地方；若没有 @Target，则该 Annotation 可以用于任何地方。
```

#### 2.1.4 @Retention(RetentionPolicy.RUNTIME)

```
前面我们说过，RetentionPolicy 是 Annotation 的策略属性，而 @Retention 的作用，就是指定 Annotation 的策略属性。

@Retention(RetentionPolicy.RUNTIME) 的意思就是指定该 Annotation 的策略是 RetentionPolicy.RUNTIME。这就意味着，编译器会将该 Annotation 信息保留在 .class 文件中，并且能被虚拟机读取。

定义 Annotation 时，@Retention 可有可无。若没有 @Retention，则默认是 RetentionPolicy.CLASS。
```

### 2.2 实例1：反射获取注解

```java
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface MyField {
    String description();

    int length();
}
```

```java
public class MyFieldTest {
    @MyField(description = "用户名", length = 12)
    private String username;

    @MyField(description = "密码", length = 13)
    private String password;

    @Test
    public void testMyField() {
        // 获取类模板
        Class c = MyFieldTest.class;

        for (Field f :
                c.getDeclaredFields()) {
            if (f.isAnnotationPresent(MyField.class)) {
                MyField annotation = f.getAnnotation(MyField.class);
                System.out.println(f.getName() + " " + annotation.description() + " " + annotation.length());
            }
        }
    }
}
```

```java
username 用户名 12
password 密码 13
```

### 2.3 应用场景1：自定义注解+拦截器 实现登录校验

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface LoginRequired {
}
```

```java
@RestController
public class IndexController {
    @GetMapping("/sourceA")
    public String sourceA() {
        return "sourceA";
    }

    @LoginRequired
    @GetMapping("/sourceB")
    public String sourceB() {
        return "sourceB";
    }
}
```

没有使用@LoginRequired直接可以访问，使用之后，可以在拦截器中获取这个注解

```java
 handlerMethod.getMethod().getAnnotation(LoginRequired.class);
```

```java
public class SourceAccessInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        System.out.println("进入拦截器了");

        // 反射获取方法上的LoginRequired注解
        HandlerMethod handlerMethod = (HandlerMethod) handler;
        LoginRequired loginRequired = handlerMethod.getMethod().getAnnotation(LoginRequired.class);
        if (loginRequired == null) {
            return true;
        }
        response.setContentType("application/json;charset=utf-8");
        response.getWriter().print("你访问的资源需要登录");
        return false;
    }

    @Override
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) throws Exception {

    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {

    }
}
```

```java
@Configuration
public class InterceptorTrainConfigurer implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SourceAccessInterceptor()).addPathPatterns("/**");
    }
}
```

### 2.4 应用场景2：自定义注解+AOP实现日志打印

先导入切面需要的依赖包

```xml
<dependency>
      <groupId>org.springframework.boot</groupId>
     <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
```

定义一个注解

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface MyLog {
}
```

定义一个切面类，见如下代码注释理解

```java
@Aspect
@Component
public class MyLogAspect {
    @Pointcut("@annotation(com.example.annotation.anno.MyLog)")
    public void logPointCut() {
    }

    // 3. 环绕通知
    @Around("logPointCut()")
    public Object logAround(ProceedingJoinPoint joinPoint) throws Throwable {
        // 获取方法名称
        String methodName = joinPoint.getSignature().getName();
        // 获取入参
        Object[] param = joinPoint.getArgs();

        StringBuilder sb = new StringBuilder();
        for (Object o : param) {
            sb.append(o + "; ");
        }
        System.out.println("进入[" + methodName + "]方法,参数为:" + sb.toString());
        return joinPoint.proceed();
    }
}
```

IndexController中写一个sourceC进行测试，加上我们的自定义注解

```java
@MyLog
@GetMapping("/sourceC/{source_name}")
public String sourceC(@PathVariable("source_name") String sourceName){
    return "你正在访问sourceC资源";
}
```

### 2.5 自定义注解—参数校验

#### 2.5.1 依赖

```xml
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <version>1.18.12</version>
</dependency>

<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
```

#### 2.5.2 声明参数注解

```java
@Target({ElementType.PARAMETER}) // PARAMETER 参数
@Retention(RetentionPolicy.RUNTIME)
public @interface ValidCom {
}
```

#### 2.5.3 声明字段注解

```java
@Documented
@Target(ElementType.FIELD) // FIELD 
@Retention(RetentionPolicy.RUNTIME)
public @interface Length {
    int maxLength() default 0;
    int minLength() default 0;
    String message() default "";
}
```

```java
@Documented
@Target(ElementType.FIELD) // FIELD
@Retention(RetentionPolicy.RUNTIME)
public @interface NotNull {
}
```

```java
@Documented
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Value {
    int maxValue();
    int minValue();
    String message() default "";
}
```

#### 2.5.4 AOP 切入

```java
@Aspect
@Component
public class ValidComAspect {
    @Pointcut("within(com.example.annotation.controller.IndexController)")
    public void validComCut() {
    }

    @Around("validComCut()")
    public Object validComCutAround(ProceedingJoinPoint joinPoint) throws Throwable {

        Object[] args = joinPoint.getArgs(); // 获取所有的参数 PersonVo(name=hahah, age=11)

        if (args.length == 0) {
            return joinPoint.proceed(args);
        }

        Signature signature = joinPoint.getSignature(); // String com.example.annotation.controller.IndexController.index(PersonVo)

        Method method = ((MethodSignature) signature).getMethod(); // 获取方法 public java.lang.String com.example.annotation.controller.IndexController.index(com.example.annotation.dto.PersonVo)

        Annotation[][] parameterAnnotations = method.getParameterAnnotations();

        for (int i = 0; i < parameterAnnotations.length; i++) {
            Object object = args[i];
            Annotation[] paramAnn = parameterAnnotations[i];

            if (object == null || paramAnn.length == 0) {
                continue;
            }

            for (Annotation annotation :
                    parameterAnnotations[i]) {
                if (annotation.annotationType().equals(ValidCom.class)) {
                    // 校验
                    validParam(object);
                }

            }
        }

        return joinPoint.proceed();
    }

    private void validParam(Object object) throws IllegalAccessException {
        Field[] declaredFields = object.getClass().getDeclaredFields();

        for (Field field :
                declaredFields) {
            Annotation[] declaredAnnotations = field.getDeclaredAnnotations();
            for (Annotation anno :
                    declaredAnnotations) {
                if (anno.annotationType().equals(NotNull.class)) {
                    field.setAccessible(true);
                    Object o = field.get(object);
                    System.out.println(o);
                    Assert.notNull(o, field.getName() + "不可为空");
                }

                if (anno.annotationType().equals(Length.class)) {
                    Length length = field.getAnnotation(Length.class);
                    field.setAccessible(true);
                    String o = (String) field.get(object);
                    Assert.isTrue(o.length() <= length.maxLength(), length.message());
                }

                if (anno.annotationType().equals(Value.class)) {
                    Value value = field.getAnnotation(Value.class);
                    field.setAccessible(true);
                    Integer o = (Integer) field.get(object);
                    Assert.isTrue(o <= value.maxValue() && o >= value.minValue(), value.message());
                }
            }
        }
    }
}
```

#### 2.5.5 实体类

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
@Builder
public class PersonVo {
    @NotNull
    @Length(maxLength = 10, minLength = 1, message = "名字长度不在范围")
    private String name;
    @Value(minValue = 18, maxValue = 28, message = "年龄长度不再范围")
    private int age;
}
```

#### 2.5.6 Controller

```java
@RestController
public class IndexController extends BasicController {

    @RequestMapping(value = "index", method = RequestMethod.POST)
    public String index(@ValidCom @RequestBody PersonVo personVo) {
        return personVo.getName() + " " + personVo.getAge();
    }
}
```

#### 2.5.7 BasicController

（不是必须，只是想增加异常处理的类，接口得到的返回结果更好看点）

```java
public class BasicController {
    @ExceptionHandler({IllegalArgumentException.class})
    public
    @ResponseBody
    Response<String> handleIllegalArgumentException(HttpServletRequest req, IllegalArgumentException exception) {
        return Response.FAIL(500, exception.getMessage());
    }
}
```

```java
public class Response<E> {
    private String status;
    private E result;
    private Integer error_code;
    private String error_msg;
    private long current_time;

    public long getCurrent_time() {
        return this.current_time;
    }

    public void setCurrent_time(long current_time) {
        this.current_time = current_time;
    }

    private Response(String status, E result, Integer error_code, String error_msg) {
        this.status = status;
        this.result = result;
        this.error_code = error_code;
        this.error_msg = error_msg;
    }

    public String getStatus() {
        return this.status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public E getResult() {
        return this.result;
    }

    public void setResult(E result) {
        this.result = result;
    }

    public Integer getError_code() {
        return this.error_code;
    }

    public void setError_code(Integer error_code) {
        this.error_code = error_code;
    }

    public String getError_msg() {
        return this.error_msg;
    }

    public void setError_msg(String error_msg) {
        this.error_msg = error_msg;
    }

    public static final <E> Response<E> SUCCESS() {
        return SUCCESS((E) null);
    }

    public static final <E> Response<E> SUCCESS(E result) {
        Response response = new Response("success", result, (Integer) null, (String) null);
        response.setCurrent_time(System.currentTimeMillis());
        return response;
    }

    public static final <E> Response<E> FAIL(Integer error_code, String error_msg) {
        return new Response("fail", (Object) null, error_code, error_msg);
    }

    public String toString() {
        return "Response{status='" + this.status + '\'' + ", result=" + this.result + ", error_code=" + this.error_code + ", error_msg='" + this.error_msg + '\'' + '}';
    }
}
```

## 3 常见注解

### 3.1 @PostConstruct

这是Java自己的注解，Java注解的说明：@PostConstruct该注解被用来修饰一个非静态的void()方法。被@PostConstruct修饰的方法会在服务器加载Servlet的时候运行，并且只会被服务器执行一次。PostConstruct在构造函数之后执行，init()方法前执行。

通常我们会是在Spring框架中使用到@PostConstruct注解，该注解的方法在整个Bean初始化中的执行顺序：

Constructor（构造方法）-> @Autowired（依赖注入） -> @PostConstruct（注释的方法）



